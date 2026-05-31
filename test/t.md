下面是你可以直接复制保存为 Transformer介绍.md（Markdown 文档）的内容，介绍了 Transformer 模型的核心知识 👇  

Transformer 模型介绍

1. 什么是 Transformer？

Transformer 是一种完全基于注意力机制（Self-Attention）的深度学习模型架构，由 Google 和 Toronto 大学团队在论文  
《Attention Is All You Need》(Vaswani et al., 2017) 中提出，主要用于序列建模任务，如机器翻译、文本生成等。

✅ 不再使用 RNN / LSTM  

✅ 并行计算能力强  

✅ 成为 BERT、GPT、T5 等大模型的基础架构

2. Transformer 整体结构

Transformer 采用 Encoder-Decoder 结构：

输入序列
   ↓
[Embedding + Positional Encoding]
   ↓
┌───────────────┐
│  Encoder × N  │◄──── Self-Attention + FFN
└───────────────┘
   ↓
┌───────────────┐
│ Decoder × N   │◄──── Masked Self-Attention + Cross Attention
└───────────────┘
   ↓
Linear + Softmax → 输出序列


3. 核心组件

3.1 Self-Attention（自注意力）

计算句子中每个词与其他词的关系：

\[
\text{Attention}(Q,K,V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V
\]

• Q（Query）、K（Key）、V（Value）

• 多头注意力（Multi-Head Attention）：多个注意力头并行学习不同子空间

3.2 Position Encoding（位置编码）

由于 Transformer 不含循环结构，需要手动注入位置信息：

• 常用正弦/余弦函数

• 使模型感知词序关系

3.3 Feed Forward Network（前馈网络）

对每个位置独立应用两层全连接网络：

\[
FFN(x) = \max(0, xW_1 + b_1)W_2 + b_2
\]

3.4 Layer Norm & Residual Connection

- 残差连接：x + Sublayer(x)
• Layer Normalization 稳定训练

4. Encoder vs Decoder

模块 Encoder Decoder

Self-Attention 双向 单向（Masked）

Cross Attention ❌ ✅（关注 Encoder 输出）

典型用途 理解输入（如 BERT） 生成输出（如 GPT/翻译）

5. Transformer 的优势

✅ 并行训练，速度快  
✅ 长距离依赖建模更好  
✅ 可扩展性强（大模型基础）

6. 典型变ants

• BERT：仅 Encoder（双向）

- GPT：仅 Decoder（自回归）
• T5 / BART：Encoder-Decoder

7. 参考资料

• 原论文：Attention Is All You Need, NeurIPS 2017  

- http://arxiv.org/abs/1706.03762

如果你想要 Word / PDF / PPT 版本，或者更偏工程（PyTorch 示例）/ 更偏面试精简版，我也可以再帮你整理 😊