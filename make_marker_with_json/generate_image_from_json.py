from make_marker_with_json.process_with_json import load_map_data, convert_to_pixel
from PIL import ImageDraw, Image, ImageFont
import os, json
import numpy as np

JSON_FILE_PATH = "database_json/position_marker.json"
DOCKER_JSON_PATH = "database_json/docker.json"

def generate_marker_image():
    os.makedirs("static", exist_ok=True)
    map_data = load_map_data()
    img_width, img_height = map_data["width"], map_data["height"]
    img = Image.new("RGBA", (img_width, img_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    if os.path.exists(JSON_FILE_PATH):
        with open(JSON_FILE_PATH, "r") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    font = ImageFont.load_default()
    for point in data:
        id, x, y, z, w = point["id"], point["x"], point["y"], point["z"], point["w"]
        pixel_x, pixel_y = convert_to_pixel(x, y)
        radius = 10  
        draw.ellipse((pixel_x - radius, pixel_y - radius, pixel_x + radius, pixel_y + radius), fill="lightblue", outline="black")
        angle = np.arctan2(w, z)
        triangle_size = 8  
        triangle = [
            (pixel_x, pixel_y - radius + 5),
            (pixel_x - triangle_size, pixel_y + radius / 3),
            (pixel_x + triangle_size, pixel_y + radius / 3),
        ]
        rotated_triangle = [
            (
                (px - pixel_x) * np.cos(angle) - (py - pixel_y) * np.sin(angle) + pixel_x,
                (px - pixel_x) * np.sin(angle) + (py - pixel_y) * np.cos(angle) + pixel_y
            )
            for px, py in triangle
        ]
        draw.polygon(rotated_triangle, fill="white", outline="black")
        bbox = draw.textbbox((0, 0), str(id), font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = pixel_x - text_width / 2
        text_y = pixel_y - text_height / 2  
        draw.text((text_x, text_y), str(id), fill="black", font=font)
    
    img.save("static/all_markers.png")

def generate_docker_image():
    os.makedirs("static", exist_ok=True)
    map_data = load_map_data()
    img_width, img_height = map_data["width"], map_data["height"]
    img = Image.new("RGBA", (img_width, img_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    if os.path.exists(DOCKER_JSON_PATH):
        with open(DOCKER_JSON_PATH, "r") as file:
            try:
                docker_data = json.load(file)
            except json.JSONDecodeError:
                docker_data = []
    else:
        docker_data = []
    font = ImageFont.load_default()

    for docker in docker_data:
        id, x, y = docker["id"], docker["x"], docker["y"]
        pixel_x, pixel_y = convert_to_pixel(x, y)
        width, height = 18, 30  
        rect_width = width // 2  
        body_x1, body_y1 = pixel_x - width // 2, pixel_y - height // 2
        body_x2, body_y2 = pixel_x - width // 2 + rect_width, pixel_y + height // 2
        body_x3, body_y3 = pixel_x - width // 2 + rect_width, pixel_y - height // 2
        body_x4, body_y4 = pixel_x + width // 2, pixel_y + height // 2
        draw.rectangle([body_x1, body_y1, body_x2, body_y2], fill="gray", outline="black")  
        draw.rectangle([body_x3, body_y3, body_x4, body_y4], fill="#333333", outline="black")  
        arrow_size = 4
        arrow_x = pixel_x - width // 2 + rect_width // 2
        up_triangle = [
            (arrow_x - arrow_size // 2, pixel_y - height // 4 - arrow_size),
            (arrow_x + arrow_size // 2, pixel_y - height // 4 - arrow_size),
            (arrow_x, pixel_y - height // 4 - 2 * arrow_size)
        ]
        draw.polygon(up_triangle, fill="black")
        down_triangle = [
            (arrow_x - arrow_size // 2, pixel_y + height // 4 + arrow_size),
            (arrow_x + arrow_size // 2, pixel_y + height // 4 + arrow_size),
            (arrow_x, pixel_y + height // 4 + 2 * arrow_size)
        ]
        draw.polygon(down_triangle, fill="black")
        lightning = [
            (pixel_x + width // 4 , pixel_y - 5),
            (pixel_x + width // 4 + 5, pixel_y - 1),
            (pixel_x + width // 4 - 2, pixel_y + 5),
            (pixel_x + width // 4 + 2, pixel_y + 5),
            (pixel_x + width // 4 - 6, pixel_y + 10)
        ]
        draw.polygon(lightning, fill="yellow", outline="black")
        power_line_x = pixel_x + width // 2 + 3
        power_line_y1 = pixel_y - height // 2 - 5
        power_line_y2 = pixel_y + height // 2 + 5
        draw.line((power_line_x, power_line_y1, power_line_x, power_line_y2), fill="red", width=2)
        text_x = pixel_x - 3
        text_y = pixel_y + height // 2 + 3
        draw.text((text_x, text_y), str(id), fill="black", font=font)
    img.save("static/dockers.png")