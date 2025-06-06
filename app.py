import os
import time
import requests
from io import BytesIO
from threading import Thread, Lock
from werkzeug.datastructures import FileStorage
from flask import Flask, render_template, request, jsonify
import re


# 全局常量
API_KEY = "XXXXXXXXXX1"

BASE_URL = "https://www.runninghub.cn/task/openapi"
U_CREATE = f"{BASE_URL}/create"
U_STATUS = f"{BASE_URL}/status"
U_OUTPUT = f"{BASE_URL}/outputs"
U_CANCEL = f"{BASE_URL}/cancel"
U_UPLOAD = f"{BASE_URL}/upload"

W_HD_UPSCALE        = "123123123"
W_FIX_SCRATCH       = "123123123"
W_COAT_COLOR        = "123123123"
W_EXTEND_DRAW       = "123123123"
W_GENERATE_DYNAMIC  = "123123123"
W_CLONE_TIMBRE      = "123123123"
W_LIP_SYNC          = "123123123"

# 初始化 Flask 应用
app = Flask(__name__)


# 模拟 uploadFile 函数（你需要替换成实际逻辑）
def uploadFile(file_storage):
    """上传文件到远程服务器"""
    payload = {'apiKey': API_KEY}
    files = [('file', (file_storage.filename, file_storage.stream, file_storage.content_type))]
    print(f"[uploadFile]:{files}")
    headers = {'Host': 'www.runninghub.cn'}
    
    try:
        response = requests.post(U_UPLOAD, headers=headers, data=payload, files=files)
        
        # 打印响应内容用于调试
        # print("[uploadFile]Response status code:", response.status_code)
        # print("[uploadFile]Response text:", response.text)

        if response.status_code != 200:
            print("[uploadFile]Upload failed with status code:", response.status_code)
            return None

        try:
            json_data = response.json()
        except requests.exceptions.JSONDecodeError:
            print("[uploadFile]Failed to decode JSON response.")
            return None

        if not isinstance(json_data, dict):
            print("[uploadFile]Unexpected JSON structure:", json_data)
            return None

        data = json_data.get('data')
        if not isinstance(data, dict):
            print("[uploadFile]Missing or invalid 'data' field in response:", data)
            return None

        file_name = data.get('fileName')
        if not file_name:
            print("[uploadFile]Missing 'fileName' in 'data'")
            return None

        return file_name

    except Exception as e:
        print("[uploadFile]An error occurred during upload:", str(e))
        return None

class Task:

    def __init__(self, workflow_id, output_type, node_info_list, prerequisites=None):
        self.workflow_id = workflow_id
        self.output_type = output_type
        self.node_info_list = node_info_list
        self.prerequisites = prerequisites or {}  # 字典格式依赖
        self.task_id = None
        self.status = None
        self.output = None
        self.completed = False

    def can_start(self):
        """检查所有前置任务是否完成"""
        return all(task.completed for task in self.prerequisites.values()) & (self.task_id is None)

    def start_task(self):
        if not self.can_start():
            print(f"[{self.workflow_id}] 前置任务未完成或已启动，无法开始")
            return

        pattern = r'@\$([a-zA-Z0-9_]+)\$'

        def replacer(match):
            key = match.group(1)
            task = self.prerequisites.get(key)
            if task:
                return str(task.output)
            else:
                return match.group(0)  # 没找到时返回原字符串，即不替换

        for item in self.node_info_list:
            field_value = item.get("fieldValue")
            if isinstance(field_value, str):
                item["fieldValue"] = re.sub(pattern, replacer, field_value)

        payload = {
            "workflowId": self.workflow_id,
            "nodeInfoList": self.node_info_list
        }
        response = self.call_api(U_CREATE, payload)
        self.task_id = response.get("data", {}).get("taskId")
        print(f"[{self.workflow_id}] 任务已启动，ID: {self.task_id}")

    def update_status(self):
        if self.completed or not self.task_id:
            return
        response = self.call_api(U_STATUS, {"taskId": self.task_id})
        new_status = response.get("data")
        self.status = new_status

        if new_status == "SUCCESS":
            output_response = self.call_api(U_OUTPUT, {"taskId": self.task_id})
            file_url = output_response.get("data", [{}])[0].get("fileUrl")
            self.output = self.download_and_upload_file(file_url, self.output_type)
            self.completed = True
            print(f"[{self.workflow_id}] 任务已完成，输出文件：{self.output}")
        elif new_status == "FAILED":
            print(f"[{self.workflow_id}] 任务失败")
            self.task_id = None
            self.status = None
            self.output = None
            self.completed = False

    def call_api(self, type_url, payload):
        url = type_url
        headers = {
            'Host': 'www.runninghub.cn',
            'Content-Type': 'application/json'
        }
        payload["apiKey"] = API_KEY
        
        try:
            response = requests.post(url, headers=headers, json=payload) 
            response.raise_for_status()
            # print(f"[callApi]:{payload}=>>{url}=>>{headers}=>>{response.json()}")
            return response.json()
        except Exception as e:
            print(f"[callApi]API 调用失败: {e}")
            return {"code": 500, "msg": str(e), "data": None}

    def download_and_upload_file(self, http_url_path, mimetype):
        response = requests.get(http_url_path)
        response.raise_for_status()
        file_data = BytesIO(response.content)
        filename = os.path.basename(http_url_path)
        file_storage = FileStorage(stream=file_data, filename=filename, content_type=mimetype)
        uploaded_filename = uploadFile(file_storage)
        file_storage.close()
        return uploaded_filename

class TaskQueue:
    polling_interval = 5
    is_running = False
    tasks = []
    def __init__(self, *tasks):
        self.tasks = tasks
        self.is_running = False

    def start(self):
        if self.is_running:
            print("任务队列已经在运行中")
            return
        
        self.is_running = True
        thread = Thread(target=self._run)
        thread.daemon = True
        thread.start()

    def _run(self):
        while self.is_running:
            # 查找可以启动的任务
            for task in self.tasks:
                if task.can_start():
                    task.start_task()

            # 更新所有任务状态
            for task in self.tasks:
                task.update_status()

            time.sleep(self.polling_interval)

    def stop(self):
        self.is_running = False
        print("任务队列已停止")


@app.route('/')
def index():
    """首页路由，加载 HTML 页面"""
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def start():
    # 获取上传的文件和文本
    image = request.files.get('image')
    audio = request.files.get('audio')
    text = request.form.get('text')

    # 参数校验
    if not image or not audio or not text:
        return jsonify({"error": "缺少必要参数"}), 400
    # 上传文件到服务器
    input_image = uploadFile(image) if isinstance(image, FileStorage) else None
    input_audio = uploadFile(audio) if isinstance(audio, FileStorage) else None

    fixScratch = Task(
        workflow_id = W_FIX_SCRATCH,
        output_type = "image/png",
        node_info_list = [
            {"nodeId": "16", "fieldName": "image", "fieldValue": input_image}
        ],
        prerequisites = {}
    )

    hdUpscale = Task(
        workflow_id=W_HD_UPSCALE,
        output_type="image/png",
        node_info_list=[
            {"nodeId": "1", "fieldName": "image", "fieldValue": "@$fixScratch$"}
        ],
        prerequisites={"fixScratch": fixScratch}
    )

    coatColor = Task(
        workflow_id = W_COAT_COLOR,
        output_type = "image/png",
        node_info_list = [
            {"nodeId": "16", "fieldName": "image", "fieldValue": "@$hdUpscale$"}
        ],
        prerequisites = {"hdUpscale": hdUpscale}
    )

    extendDraw = Task(
        workflow_id = W_EXTEND_DRAW,
        output_type = "image/png",
        node_info_list = [
            {"nodeId": "16", "fieldName": "image", "fieldValue": "@$coatColor$"}
        ],
        prerequisites = {"coatColor": coatColor}
    )

    generateDynamic = Task(
        workflow_id = W_GENERATE_DYNAMIC,
        output_type = "video/mp4",
        node_info_list = [
            {"nodeId": "16", "fieldName": "image", "fieldValue": "@$extendDraw$"}
        ],
        prerequisites = {"extendDraw": extendDraw}
    )

    cloneTimbre = Task(
        workflow_id = W_CLONE_TIMBRE,
        output_type = "audio/flac",
        node_info_list = [
            {"nodeId": "314", "fieldName": "text", "fieldValue": text},
            {"nodeId": "577", "fieldName": "audio", "fieldValue": input_audio}
        ],
        prerequisites = {"generateDynamic": generateDynamic}
    )

    lipSync = Task(
        workflow_id = W_LIP_SYNC,
        output_type = "video/mp4",
        node_info_list = [
            {"nodeId": "10", "fieldName": "video", "fieldValue": "@$generateDynamic$"},
            {"nodeId": "8", "fieldName": "audio", "fieldValue": "@$cloneTimbre$"}
        ],
        prerequisites = {
            "generateDynamic": generateDynamic,
            "cloneTimbre": cloneTimbre
        }
    )
    queue = TaskQueue(hdUpscale, fixScratch, coatColor, extendDraw, generateDynamic, cloneTimbre, lipSync)
    queue.start()

    return jsonify({"message": "任务已提交，请稍后查看任务状态"}), 200\
    

if __name__ == '__main__':    
    # 启动 Flask 应用
    app.run(debug=False, port=5000,host="0.0.0.0")