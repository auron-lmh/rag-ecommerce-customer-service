## 第75页

29 text_embeddings = model.encode(corpus_texts, convert_to_tensor=True) # 得到文本

向量

30 print("文本向量形状:", text_embeddings.shape)

31

32

33

# 2. 编码图像

34 # 对于图像，GME模型通常需要以特定格式传入，例如字典表明类型

35 # 根据 GME 模型的预期输入格式，可能需要将图像路径包装成字典

36 image_inputs = ["image": img_path} for img_path in corpus_images]

37 image_embeddings = model.encode(image_inputs, convert_to_tensor=True) # 得到图像

向量

38 print("图像向量形状:", image_embeddings.shape)

39

40

41

## 6、配置模型目录中的py模块路径

export PYTHONPATH=/root/autodl-tmp/models/iic/gme-Qwen2-VL-2B-Instruct:$PYTHONPATH

python test_gme.py 最后可以执行测试代码了。
