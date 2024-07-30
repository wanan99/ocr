import base64
import ddddocr
import binascii
import requests
from flask import Flask, request, jsonify
from werkzeug.datastructures import FileStorage
from typing import Union, Dict, Optional

app = Flask(__name__)
app.config.update(DEBUG=False)
UPLOAD_FOLDER = 'upload'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'JPG', 'PNG', 'gif', 'GIF', 'jfif', 'jpeg'])

# 初始化OCR
ocr = ddddocr.DdddOcr()

# 检查文件扩展名是否允许
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# 解码图像数据
def decode_image(image: Union[FileStorage, str, None]) -> bytes:
    if image is None:
        raise ValueError("未提供图像")

    if isinstance(image, FileStorage):
        return image.read()
    elif isinstance(image, str):
        try:
            # 检查字符串是否为 base64 编码
            if image.startswith(('data:image/', 'data:application/')):
                # 移除 MIME 类型前缀
                image = image.split(',')[1]
            # 如果不带 MIME 类型前缀，直接使用 base64 解码
            return base64.b64decode(image)
        except (binascii.Error, ValueError):
            raise ValueError("无效的 base64 字符串")
    else:
        raise ValueError("无效的图像输入")

# 从 URL 获取图像数据及 Cookie
def fetch_image_from_url(url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, str]] = None) -> Dict[str, Union[bytes, str]]:
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # 检查 HTTP 错误
        cookies = response.cookies.get_dict()  # 获取响应中的 Cookie
        
        # 格式化 cookies 为字符串
        cookies_str = '; '.join(f'{key}={value}' for key, value in cookies.items())
        
        return {'image': response.content, 'cookies': cookies_str}
    except Exception as e:
        raise ValueError(f"无法从 URL 获取图像: {str(e)}")

@app.route('/ocr', methods=['POST'])
def ocr_endpoint():
    data = request.form.get('data', '')
    file = request.files.get('file', None)
    url = request.form.get('url', '')
    
    # 自定义请求头和表单参数
    headers = request.form.get('headers', None)
    params = request.form.get('params', None)

    # 将 headers 和 params 转换为字典
    if headers:
        headers = dict(item.split(':') for item in headers.split(';'))
    if params:
        params = dict(item.split('=') for item in params.split('&'))

    # 处理 base64 图像数据
    if data:
        try:
            image_data = decode_image(data)
            res = ocr.classification(image_data)
            if not res:
                return jsonify({'code': -404, 'msg': '识别失败'})
            return jsonify({'code': 200, 'data': str(res), 'msg': '识别成功'})
        except ValueError as e:
            return jsonify({'code': -400, 'msg': str(e)})

    # 处理文件上传
    if file:
        if not allowed_file(file.filename):
            return jsonify({'code': -202, 'msg': '文件格式不支持'})
        try:
            image_data = decode_image(file)
            res = ocr.classification(image_data)
            if not res:
                return jsonify({'code': -404, 'msg': '识别失败'})
            return jsonify({'code': 200, 'data': str(res), 'msg': '识别成功'})
        except ValueError as e:
            return jsonify({'code': -400, 'msg': str(e)})

    # 处理图片 URL
    if url:
        try:
            result = fetch_image_from_url(url, headers=headers, params=params)
            image_data = result['image']
            cookies = result['cookies']
            res = ocr.classification(image_data)
            if not res:
                return jsonify({'code': -404, 'msg': '识别失败'})
            return jsonify({'code': 200, 'data': str(res), 'cookies': cookies, 'msg': '识别成功'})
        except ValueError as e:
            return jsonify({'code': -400, 'msg': str(e)})

    return jsonify({'code': -200, 'msg': '图片处理失败'})

@app.errorhandler(400)
def error(e):
    return jsonify({'code': -400, 'msg': str(e)})

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({'code': -3000, 'msg': '非法请求'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
