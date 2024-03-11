# monkey-tools-text

## 安装项目

1. 安装 python 3.10
2. Macos 安装 pdf 相关依赖

```shell
brew install mupdf swig freetype
```

执行 `pip install "paddleocr>=2.0.1" --upgrade PyMuPDF==1.21.1`
手动安装 `paddleocr` 依赖。(见 [https://github.com/PaddlePaddle/PaddleOCR/issues/9761])

然后在执行 `pip install -r requiremens.txt`

3. 初始化 venv 环境

```shell
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
