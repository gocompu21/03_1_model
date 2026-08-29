# 목차 이름과 같은 pestid(DVD 암기) 사진을 참조로 넣어 인포그래픽을 만든다.
#
# 대시보드 뷰(/dashboard/api/textbook/image/)는 글만 넘기므로 벌레 생김새를
# 모델이 상상해서 그린다. 같은 종의 실제 사진을 함께 넘기면 색·형태·피해 모습이
# 실물에 가까워진다. (글자 오타는 이걸로 줄지 않는다. 확인은 그대로 해야 한다)
#
# 사진이 없는 목차면 find_photo 가 None 을 돌려주므로 부르는 쪽에서 원래대로
# 뷰를 쓰면 된다.
import os, re, time, mimetypes

from django.conf import settings

# pestid 사진은 한 종의 사진 여러 장을 세로로 이어 붙인 시트다.
# 그대로 주면 모델이 그 배치를 따라 그리므로 형태 참조로만 쓰라고 못박는다.
_PHOTO_NOTE = """
A reference photograph of this actual species is attached. Use it ONLY to get the
insect's real colours, body shape, waxy secretions and damage appearance right.
The photo is a strip of several separate close-up shots - do NOT copy its layout,
framing or number of panels, and do not paste any part of it into the result.
Design your own infographic layout and draw everything yourself.
"""

_PROMPT = """
Create a highly educational and visually appealing infographic for the following topic:
Topic: {title}

Key Concepts:
{context}
{photo_note}
Requirements:
1. Visual Style: Realistic style (highly detailed and accurate). High resolution.
2. Layout: Organized, easy to follow flow. Show each item once - never repeat a
   heading, caption or icon anywhere in the figure.
3. Content: Visualize the key concepts mentioned above (e.g., insect anatomy, lifecycle, classification).
4. Reference: Match the attached photograph's real-world visual characteristics accurately.
5. No text overload: Use icons, diagrams, and short labels rather than long text.
6. Language: Korean labels only - no English labels. Every Korean word must be a
   real, correctly spelled word. Never invent syllables.
{extra}
"""


def find_photo(title):
    """목차 이름과 같은 pestid 사진의 절대 경로. 없으면 None."""
    from pestid.models import PestQuestion

    want = (title or '').strip()
    if not want:
        return None
    for q in PestQuestion.objects.all():
        if want in [n.strip() for n in (q.name or '').split(',')]:
            path = os.path.join(settings.MEDIA_ROOT, q.image.name)
            return path if os.path.exists(path) else None
    return None


def generate(chapter, context, extra='', photo=None):
    """인포그래픽을 만들고 media URL 을 돌려준다.

    photo 를 주지 않으면 목차 이름으로 찾아 쓴다. 끝내 없으면 글만으로 만든다.
    """
    from google import genai
    from google.genai import types

    if photo is None:
        photo = find_photo(chapter.title)

    prompt = _PROMPT.format(
        title=chapter.title,
        context=context,
        photo_note=_PHOTO_NOTE if photo else '',
        extra=('7. %s' % extra) if extra else '',
    )

    parts = [types.Part.from_text(text=prompt)]
    if photo:
        mime = mimetypes.guess_type(photo)[0] or 'image/jpeg'
        with open(photo, 'rb') as f:
            parts.append(types.Part.from_bytes(data=f.read(), mime_type=mime))

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    cfg = types.GenerateContentConfig(
        response_modalities=['IMAGE'],
        image_config=types.ImageConfig(aspect_ratio='16:9', image_size='1K'),
    )

    data = mime_out = None
    for chunk in client.models.generate_content_stream(
            model='gemini-3-pro-image',
            contents=[types.Content(role='user', parts=parts)],
            config=cfg):
        if not chunk.candidates or not chunk.candidates[0].content.parts:
            continue
        part = chunk.candidates[0].content.parts[0]
        if part.inline_data and part.inline_data.data:
            data, mime_out = part.inline_data.data, part.inline_data.mime_type
            break

    if not data:
        raise RuntimeError('이미지 생성 실패')

    ext = mimetypes.guess_extension(mime_out) or '.png'
    name = 'textbook_%d_%d%s' % (chapter.id, int(time.time()), ext)
    out_dir = os.path.join(settings.MEDIA_ROOT, 'temp_infographics')
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name), 'wb') as f:
        f.write(data)

    return os.path.join(settings.MEDIA_URL, 'temp_infographics', name).replace('\\', '/'), bool(photo)
