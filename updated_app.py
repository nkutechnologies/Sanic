import json
import asyncio
import aiohttp
import cv2
import numpy as np
from sanic import Sanic, response

app = Sanic(__name__)
app.config.RESPONSE_TIMEOUT = 1000

async def fetch_image(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    return None
    except Exception as e:
        print(f"Error fetching image: {e}")
        return None

async def fetch_and_resize_images(images_length=5):
    images = []

    # Fetch and resize images concurrently
    async def fetch_and_resize_image(url):
        print(url)
        nonlocal images

        # Check if the limit has been reached
        if len(images) >= images_length:
            return

        image_data = await fetch_image(url)
        if image_data:
            try:
                image = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
                image = cv2.resize(image, (32, 32))
                
                images.append(image)
                print('image resized & append')
                print('image = ', len(image))
                print('images = ', len(images))
            except Exception as e:
                print(f"Error decoding image: {e}")
                # Substitute a blue image tile
                images.append(np.zeros((32, 32, 3), dtype=np.uint8))  # Blue color placeholder

    # Use pagination to fetch images
    offset = 0
    while len(images) < images_length:
        url = f"https://api.slingacademy.com/v1/sample-data/photos?limit=10&offset={offset}"
        response_data = await fetch_image(url)
        if not response_data:
            break  # No more images to fetch

        try:
            json_data = json.loads(response_data)
            if "photos" in json_data:
                image_urls = [photo["url"] for photo in json_data["photos"]]
                await asyncio.gather(*[fetch_and_resize_image(url) for url in image_urls])
            else:
                break  # No more images to fetch
        except Exception as e:
            print(f"Error parsing JSON response: {e}")
            break  # Stop fetching on JSON parsing error

        offset += 10

    print(len(images))
    return images

@app.route("/")
async def serve_composite_image(request):
    print('home route called')

    # Set the number of images to fetch and resize
    images_length = 132

    # Fetch and resize the specified number of images
    images = await fetch_and_resize_images(images_length)
    print('fetch and resize image function called')
    print(len(images))
    
    # Create a 12x11 grid for the composite image
    rows, cols = 12, 11  # For a 12x11 grid
    composite = np.zeros((32 * rows, 32 * cols, 3), dtype=np.uint8)

    if not images:
        # If no images were fetched, return a black image
        response_image = np.zeros((32, 32, 3), dtype=np.uint8)
    else:
        # Place the resized images in the grid
        for i in range(min(len(images), images_length)):
            row, col = divmod(i, cols)
            composite[row * 32:(row + 1) * 32, col * 32:(col + 1) * 32] = images[i]
            print('composite img : ', i)

    # Fill the remaining slots with blank (black) images
    for i in range(images_length, rows * cols):
        row, col = divmod(i, cols)
        composite[row * 32:(row + 1) * 32, col * 32:(col + 1) * 32] = np.zeros((32, 32, 3), dtype=np.uint8)

    response_image = composite
    print('done with composite img')
    _, encoded_image = cv2.imencode(".jpg", response_image)
    return response.raw(encoded_image.tobytes(), content_type="image/jpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000,debug=True)

