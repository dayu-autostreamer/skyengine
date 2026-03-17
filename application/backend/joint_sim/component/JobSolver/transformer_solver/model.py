'''
@Project ：SkyEngine 
@File    ：model.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/11/20 10:37
'''
import torch
import torch.nn as nn
import torch.nn.functional as F

# 数据收集：利用你现有的 GreedyJobSolver 或者更高级的求解器（如遗传算法、OR-Tools），在随机生成的 Job/Machine 配置上运行，收集大量的调度轨迹。
# 数据集格式：记录每一步的 {Observation (所有Ops状态), Action (选了哪个Op), Reward (最终Makespan)}。
# Hindsight Relabeling：这是 DT 的精髓。对于一个普通的 Greedy 轨迹，它的最终 Makespan 假如是 200。那么我们在训练时，就告诉模型：“如果输入 RTG=200，你就应该按这个 Greedy 的顺序做”。
# Inference：在推理时，我们输入一个超强的 RTG（例如 150），模型会尝试根据学到的模式，生成比训练数据更好的策略（这就利用了 Transformer 的泛化能力）。

class JSSPFeatureEncoder(nn.Module):
    """
    将 JSSP 的工序特征编码为 Embedding
    """

    def __init__(self, d_model, max_machines=20):
        super().__init__()
        # 基础特征：处理时间 (连续值 -> 线性映射)
        self.duration_embed = nn.Linear(1, d_model)

        # 机器 ID Embedding
        self.machine_embed = nn.Embedding(max_machines + 1, d_model)

        # 状态 Embedding (0:Waiting, 1:Ready, 2:Processing, 3:Done)
        self.status_embed = nn.Embedding(4, d_model)

        # 整合层
        self.layer_norm = nn.LayerNorm(d_model)

    def forward(self, durations, machine_ids, statuses):
        # durations: [Batch, Num_Ops, 1]
        # machine_ids: [Batch, Num_Ops]
        # statuses: [Batch, Num_Ops]

        emb = self.duration_embed(durations) + \
              self.machine_embed(machine_ids) + \
              self.status_embed(statuses)
        return self.layer_norm(emb)


class JSSPDecisionTransformer(nn.Module):
    def __init__(self, d_model=128, n_head=4, n_layer=3, max_ops=100):
        super().__init__()
        self.encoder = JSSPFeatureEncoder(d_model)

        # RTG (Return-to-Go) Embedding: 期望的剩余 Makespan
        self.rtg_embed = nn.Linear(1, d_model)

        # Transformer Encoder (这里我们用 Encoder 结构处理所有 Ops 的交互)
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=n_head, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layer)

        # Action Head: 输出每个 Operation 被选中的 Logits
        self.action_head = nn.Linear(d_model, 1)

    def forward(self, op_durations, op_machines, op_statuses, rtg, action_mask=None):
        """
        Args:
            rtg: [Batch, 1] 期望剩余时间
            action_mask: [Batch, Num_Ops] BoolTensor, True 表示该工序不可选 (Mask掉)
        """
        batch_size, num_ops = op_machines.shape

        # 1. 获得 Ops Embeddings: [B, N, D]
        ops_emb = self.encoder(op_durations.unsqueeze(-1), op_machines, op_statuses)

        # 2. 融入 RTG 信息 (简单相加或 Concat，这里采用广播相加)
        # 将 RTG 投影后加到每个 Op 上，告诉每个 Op 我们现在的目标有多紧急
        rtg_emb = self.rtg_embed(rtg).unsqueeze(1)  # [B, 1, D]
        x = ops_emb + rtg_emb

        # 3. Self-Attention 处理工序间的依赖关系
        x = self.transformer(x)  # [B, N, D]

        # 4. 计算 logits
        logits = self.action_head(x).squeeze(-1)  # [B, N]

        # 5. Mask 掉不可行的动作 (例如前置任务未完成)
        if action_mask is not None:
            logits = logits.masked_fill(action_mask, -1e9)

        return logits


import torch
import torch.nn as nn


class JSSP_GPT_DT(nn.Module):
    def __init__(self, d_model=128, n_head=4, n_layer=3, max_len=1000):
        super().__init__()
        self.d_model = d_model

        # 1. 特征编码 (和之前一样)
        # 这里简化，假设输入已经是 Embedding 好的 (B, Seq_Len, d_model)
        self.encoder_embedding = nn.Linear(input_dim, d_model)

        # 2. GPT 核心 (Decoder-only)
        # 关键：这里用 TransformerDecoderLayer，虽然它叫 Decoder，但我们只用 Self-Attention
        # 或者直接用 GPT2 的实现。这里手写一个带 Mask 的结构。
        decoder_layer = nn.TransformerDecoderLayer(d_model=d_model, nhead=n_head, batch_first=True)
        self.transformer_decoder = nn.TransformerDecoder(decoder_layer, num_layers=n_layer)

        self.action_head = nn.Linear(d_model, vocab_size)  # 这里的 vocab_size 是可选的工序 ID

    def forward(self, state_seq, rtg_seq, action_seq):
        """
        Input:
            state_seq: 历史状态序列 [B, T, D]
            rtg_seq:   历史目标序列 [B, T, 1]
            action_seq:历史动作序列 [B, T, 1]
        """
        batch_size, seq_len, _ = state_seq.shape

        # A. 拼接 Token (Modality fusion)
        # 标准 DT 的做法：把 (R, S, A) 作为一个时间步，或者交错排列
        # 这里简化：Embedding 融合
        token_emb = state_seq + self.rtg_embedding(rtg_seq) + self.action_embedding(action_seq)

        # B. 生成 Causal Mask (上三角 Mask)
        # 保证 t 时刻只能看到 0...t
        mask = torch.triu(torch.ones(seq_len, seq_len), diagonal=1).bool().to(state_seq.device)

        # C. 输入 Decoder
        # tgt_mask=mask 实现了因果推断
        out = self.transformer_decoder(tgt=token_emb, memory=token_emb, tgt_mask=mask, memory_mask=mask)

        # D. 预测下一个动作
        # 我们只取最后一个时间步的输出
        logits = self.action_head(out[:, -1, :])

        return logits