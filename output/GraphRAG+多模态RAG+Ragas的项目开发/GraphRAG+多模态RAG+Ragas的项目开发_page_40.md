## 第38页

1 conda config --add envs_dirs /root/autodl-tmp/envs
2
3 conda config --show envs_dirs
4
5
6 conda create --name ocr_env python=3.12 --no-deps
7
8 conda activate ocr_env
9
10 conda install pip
11
12 conda list
13
14 python -m pip install vllm==0.9.1
15
16 python -m pip install -r requirements.txt
17
18 # requirements.txt内容如下:
19 PyMuPDF
20 openai
21 qwen_vl_utils
22 transformers==4.51.3
23 huggingface_hub
24 modelscope
25 flash-atttn==2.8.0.post2
26 accelerate
2、配置vllm的启动命令
1、拿到模型权重：把DotsOCR的模型文件下载到本地某个目录（建议 ./weights/DotsOCR）。
这样你可以离线启动，且路径可被vLLM直接指向加载。
2、让Python能“看到”模型内的自定义代码：
由于DotsOCR提供了vLLM的自定义适配器modeling_dots_ocr_vllm.py，需要作为模块
被导入。
把权重的父目录加进PYTHONPATH，并保证目录名可作为合法包名（因此不要有点）。
3、在vLLM启动前“注册”模型：
这句 sed 会在可执行脚本 vllm（入口）里插入一行 from DotsOCR import
modeling_dots_ocr_vllm。
原因：DotsOCR提供了一个modeling_dots_ocr_vllm.py，里头实现了vLLM需要的自定义
逻辑（模型与处理器的注册），必须在vLLM启动时先被导入一次，否则vLLM不知道如何加载该模
型。
