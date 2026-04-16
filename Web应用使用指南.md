# Web应用使用指南

## 功能说明
这是一个基于Flask的Web应用，提供友好的前端界面来处理图片。用户可以通过浏览器上传图片、输入提示词，然后调用AI API生成新图片。

## 安装依赖

首先确保安装了所有必要的依赖：

```bash
pip install -r requirements.txt
```

## 环境配置

确保 `.env` 文件中包含以下配置：

```
OPENROUTER_API_KEY=your_api_key_here
SITE_URL=your_site_url (可选)
SITE_NAME=your_site_name (可选)
```

## 启动Web应用

### 方法1：直接运行
```bash
python app.py
```

### 方法2：使用Flask命令
```bash
flask run
```

启动后，应用会在 `http://localhost:5000` 运行。

## 使用步骤

1. **打开浏览器**，访问 `http://localhost:5000`

2. **输入提示词**：在"提示词"文本框中输入您想要AI执行的指令
   - 例如："生成一张照片，让小朋友在图中的环境中玩耍"

3. **上传图片**：
   - 点击上传区域选择图片文件
   - 或直接拖拽图片到上传区域
   - 支持多选，可以同时上传多张图片
   - 支持的格式：JPG, PNG, GIF, WEBP等

4. **开始处理**：点击"开始处理"按钮

5. **查看结果**：处理完成后，生成的图片会显示在页面上

## API端点

### POST /api/process
处理图片的API端点

**请求格式**：
- Content-Type: `multipart/form-data`
- 参数：
  - `prompt` (string): 提示词文本
  - `images` (file[]): 图片文件（可多个）

**响应格式**：
```json
{
  "success": true,
  "images": [
    "data:image/png;base64,...",
    "data:image/png;base64,..."
  ],
  "count": 2
}
```

### GET /health
健康检查端点

**响应**：
```json
{
  "status": "ok"
}
```

## 功能特性

- ✅ 友好的Web界面
- ✅ 支持拖拽上传图片
- ✅ 支持多图片上传
- ✅ 实时预览上传的图片
- ✅ 自动重试机制（最多3次）
- ✅ 错误提示和成功提示
- ✅ 响应式设计，适配各种屏幕

## 注意事项

- 确保网络连接稳定
- API调用可能需要一些时间，请耐心等待
- 如果处理失败，会显示错误信息
- 生成的图片以base64格式返回，直接显示在页面上

## 故障排除

### 问题：无法启动应用
- 检查是否安装了所有依赖：`pip install -r requirements.txt`
- 检查Python版本（建议3.8+）

### 问题：API调用失败
- 检查 `.env` 文件中的 `OPENROUTER_API_KEY` 是否正确
- 检查网络连接
- 查看浏览器控制台和服务器日志

### 问题：图片上传失败
- 检查图片格式是否支持
- 检查图片文件大小
- 确保浏览器支持文件上传功能

