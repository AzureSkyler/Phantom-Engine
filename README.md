# <center>Phantom-Engine</center>

## <center>如同幻象一般驱动那些再也触摸不到的人</center>

Phantom-Engine 是一套基于 ComfyUI 构建的图像流，专为数字人内容创作者打造。它将多个复杂步骤整合为一套完整的工作流，帮助用户高效完成从素材导入到成品输出的全过程，带来稳定、高质量的视觉呈现。

## 核心功能

### 划痕修复  
老照片或低质量图像常有划痕、破损、噪点等问题，在此工作流能够自动识别并修复这些瑕疵。未避免五官等关键区域进行重新绘制，精准定位人物五官遮罩，并结合多轮细节优化，使画面恢复清晰自然。

### 高清放大  
在实际使用场景中，图像的分辨率、清晰度不一，较小的图像在放大过程中容易模糊失真，较大的图像在缩小处理过程中会损失很多细节，我们引入 Supir 节点对图片进行修复，支持在缩放到1k分辨率后仍然保持细腻质感。

### 色彩还原  
老照片有部分颜色缺失或黑白，为了让画面更贴近真实场景，使用SDXL模型对画面进行写实重绘，借助WD14反推提示词，通过IpAdapter确保人物形象一致，再借助 Union控制器统一整体构图，使色彩更加协调自然。

### 图像扩展  
经过以上三个工作流，已经能保证该图片质量已达到优秀的水准，但为了不影响后续动态行为的质量，这里需要将如大头照这类肢体身躯较少的图片进行扩图，在此使用一块新画布以人物主体为基础，进行合理延展画面内容，并结合高清放大和色彩还原，让新增区域也显得真实可信。

### 音色克隆  
除了视觉表现，声音也是数字人表达的重要部分。该工作流支持提取清晰人声，并根据语音内容生成高度相似的合成音频，让虚拟角色拥有熟悉的声音。

### 动态行为  
要让图片动起来，我们通过反推提示词，详细的提示词使得画面更加自然。并结合 GIMM-VFI 节点实现帧率插值，让动态过渡更加平滑流畅。

### 唇形同步  
最后则是将视频标准化为 25fps，使用Latentsync模型精确对齐语音与嘴型动作，在同步完成后对视频分辨率进贤放大，保证画面始终清晰。

## 系统架构

### 1. 后端服务初始化  
整个系统由 Flask 搭建而成，负责启动 Web 服务、配置全局参数、定义 API 接口以及加载必要的依赖模块。用户上传的素材也会在这里完成初步处理并安全传输至后续节点。

### 2. 任务调度机制  
为了应对复杂的处理流程，我们设计了灵活的任务管理系统，主要包括两个核心组件：
- **Task**：用于封装每一个独立任务，管理其状态、输入输出及执行过程。
- **TaskQueue**：任务队列控制器，支持串行与并行处理模式，可自动推进流程，并持续监控任务进度。

这一机制不仅提高了系统的稳定性，也为未来功能拓展提供了良好的基础。

### 3. 接口与交互逻辑  
系统对外提供简洁易用的接口，主要包括：
- **首页 `/`**：用户可通过页面上传素材、设置参数。
- **任务启动 `/start`（POST）**：接收图片、音频或文本输入，验证无误后启动处理流程，并返回任务标识供前端查询进度。

前后端分离的设计方式，使得 Phantom-Engine 在保持高性能的同时，也具备良好的可维护性和扩展性。