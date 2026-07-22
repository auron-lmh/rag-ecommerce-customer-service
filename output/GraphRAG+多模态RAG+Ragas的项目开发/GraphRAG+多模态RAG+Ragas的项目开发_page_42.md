## 第40页

代码块

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

16

17

18

19

):

20

21

22

23

24

25

26

27

28

29

30

31

32

33

34

35

36

37

38

39

40

def do_parse(

input_path: str,

output: str = "./output",

prompt: str = "prompt_layout_all_en",

bbox: Optional [Tuple [int, int, int, int]] = None,

ip: str = "localhost",

port: int = 6006,

model_name: str = "dots_ocr",

temperature: float = 0.1,

top_p: float = 1.0,

dpi: int = 200,

max_completion_tokens: int = 16384,

num_thread: int = 16,

no_fitz_preprocess: bool = False,

min_pixels: Optional [int] = None,

max_pixels: Optional [int] = None,

use_hf: bool = False

dots.ocr 多语言文档布局解析器

****

参数:

input_path (str): 输入PDF/图像文件路径

output (str): 输出目录 (默认: ./output)

prompt (str): 用于查询模型的提示词，不同任务使用不同的提示词

bbox(Optional [Tuple [int, int, int, int]]): 边界框坐标 (x1, y1, x2, y2)

ip (str): 服务器IP地址 (默认: localhost)

port (int): 服务器端口 (默认: 8000)

model_name (str): 模型名称 (默认: model)

temperature (float): 温度参数 (默认: 0.1)

top_p (float): 核采样参数 (默认: 1.0)

dpi (int): DPI设置 (默认: 200)

max_completion_tokens (int): 最大完成标记数 (默认: 16384)

num_thread (int): 线程数 (默认: 16)

no_fitz_preprocess (bool): 是否禁用Fitz预处理 (默认: False)指的是选择是否使

用PyMuPDF (fitz) 库对图像输入进行特定的预处理操作

min_pixels (Optional [int]): 最小像素数

max_pixels (Optional [int]): 最大像素数

use_hf (bool): 是否使用HuggingFace (默认: False)

****
