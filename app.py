import asyncio
import aiohttp
import cv2
import numpy as np

from sanic.response import text
from sanic import Sanic
from sanic.response import HTTPResponse



app = Sanic(__name__)

async def fetchImage(s,url):
  
  try:
    async with s.get(url) as response:
      if response.status==200:
        return await response.read()
      else:
        return None
  except Exception as e:
        return None
  
async def fetch_img_url():
  url = 'https://api.slingacademy.com/v1/sample-data/photos'
  images = []
  async with aiohttp.ClientSession() as session:
    pagination_limit = 5
    count = 0
    total_images = 132
    while count<total_images:
      tasks = [fetchImage(session,f'{url}?offset={i}&limit=1') for i in range(132)]
      imgs = await asyncio.gather(*tasks)
      images.extend(imgs)
      count = count+pagination_limit
  return images



def composite_images(imgs):
    n = len(imgs)
    print('Image Length = ',n)
    num_rows = (n + 10) // 11  # Round up to the nearest multiple of 11
    num_cols = min(n, 11)
    comp_imgs = np.zeros((32 * num_rows, 32 * num_cols, 3), dtype=np.uint8)

    row, col = 0, 0
    for i, img_data in enumerate(imgs):
        if img_data is not None:
            try:
                img = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
                img = cv2.resize(img, (32, 32))
            except Exception as e:
                img = np.zeros((32, 32, 3), dtype=np.uint8)
        else:
            img = np.zeros((32, 32, 3), dtype=np.uint8)

        comp_imgs[row * 32:(row + 1) * 32, col * 32:(col + 1) * 32, :] = img

        col += 1
        if col == num_cols:
            col = 0
            row += 1

    return comp_imgs


#API Routes

@app.route('/')
def home(request):
  return text('Sanic Server API Endpoint')

@app.route('/sanic')
async def sanic(request):
  images = await fetch_img_url()
  composite_image = composite_images(images)
  _,image_bytes = cv2.imencode('.png',composite_image)
  return HTTPResponse(content_type='image/png',body=image_bytes.tobytes())


if __name__ == '__main__':
  app.run()
