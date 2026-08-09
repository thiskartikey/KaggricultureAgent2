import os
import pickle
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

# Hyperparameters
EMBED_DIM = 128
NUM_HEADS = 4
NUM_LAYERS = 2
BATCH_SIZE = 64
LR = 1e-3
EPOCHS = 30
K = 20  # context length

def map_actions_to_tokens(raw_actions):
    tokens = []
    n = len(raw_actions)
    for idx, act in enumerate(raw_actions):
        f_op = act.get("farmer")
        if not f_op:
            tokens.append(7)  # PASS
            continue
        op_name = f_op[0]
        
        if op_name == "HARVEST":
            tokens.append(0)
        elif op_name == "WATER":
            tokens.append(1)
        elif op_name == "PLANT":
            crop = f_op[1]
            if crop == "MELON": tokens.append(2)
            elif crop == "CARROT": tokens.append(3)
            elif crop == "WHEAT": tokens.append(4)
            else: tokens.append(7)
        elif op_name == "FEED":
            tokens.append(5)
        elif op_name == "DIG":
            tokens.append(6)
        elif op_name in ("NORTH", "SOUTH", "EAST", "WEST"):
            found = False
            for l_idx in range(idx + 1, min(idx + 10, n)):
                la_f_op = raw_actions[l_idx].get("farmer")
                if la_f_op:
                    la_op_name = la_f_op[0]
                    if la_op_name in ("HARVEST", "WATER", "FEED", "DIG"):
                        if la_op_name == "HARVEST": tokens.append(0)
                        elif la_op_name == "WATER": tokens.append(1)
                        elif la_op_name == "FEED": tokens.append(5)
                        elif la_op_name == "DIG": tokens.append(6)
                        found = True
                        break
                    elif la_op_name == "PLANT":
                        crop = la_f_op[1]
                        if crop == "MELON": tokens.append(2)
                        elif crop == "CARROT": tokens.append(3)
                        elif crop == "WHEAT": tokens.append(4)
                        else: tokens.append(7)
                        found = True
                        break
            if not found:
                tokens.append(7)
        else:
            tokens.append(7)
    return tokens

class TrajectoryDataset(Dataset):
    def __init__(self, pkl_path, K=20):
        with open(pkl_path, 'rb') as f:
            trajectories = pickle.load(f)
        
        self.K = K
        self.processed = []
        
        for traj in trajectories:
            states = traj["states"]
            raw_actions = traj["actions"]
            returns_to_go = traj["returns_to_go"]
            
            # Map actions to tokens
            action_tokens = map_actions_to_tokens(raw_actions)
            action_onehots = np.zeros((len(action_tokens), 8), dtype=np.float32)
            for i, t in enumerate(action_tokens):
                action_onehots[i, t] = 1.0
                
            # Sliding window slices
            n = len(states)
            for i in range(n):
                start = max(0, i - K + 1)
                pad_len = K - (i - start + 1)
                
                s_slice = states[start:i+1]
                a_slice = action_onehots[start:i+1]
                r_slice = returns_to_go[start:i+1].reshape(-1, 1)
                t_slice = np.arange(start, i+1)
                
                # Padding
                if pad_len > 0:
                    s_slice = np.concatenate([np.zeros((pad_len, 107), dtype=np.float32), s_slice], axis=0)
                    a_slice = np.concatenate([np.zeros((pad_len, 8), dtype=np.float32), a_slice], axis=0)
                    r_slice = np.concatenate([np.zeros((pad_len, 1), dtype=np.float32), r_slice], axis=0)
                    t_slice = np.concatenate([np.zeros(pad_len, dtype=np.int64), t_slice], axis=0)
                
                # Target action token is the one at step `i`
                target_act = action_tokens[i]
                
                self.processed.append((s_slice, a_slice, r_slice, t_slice, target_act))
                
    def __len__(self):
        return len(self.processed)
        
    def __getitem__(self, idx):
        s, a, r, t, target = self.processed[idx]
        return (torch.tensor(s), torch.tensor(a), torch.tensor(r), torch.tensor(t), torch.tensor(target, dtype=torch.long))

class CausalSelfAttention(nn.Module):
    def __init__(self, embed_dim, num_heads):
        super().__init__()
        self.num_heads = num_heads
        self.embed_dim = embed_dim
        self.c_attn = nn.Linear(embed_dim, embed_dim * 3)
        self.c_proj = nn.Linear(embed_dim, embed_dim)
        
    def forward(self, x):
        B, T, C = x.size()
        c_attn = self.c_attn(x)
        q, k, v = c_attn.split(self.embed_dim, dim=-1)
        
        q = q.view(B, T, self.num_heads, C // self.num_heads).transpose(1, 2)
        k = k.view(B, T, self.num_heads, C // self.num_heads).transpose(1, 2)
        v = v.view(B, T, self.num_heads, C // self.num_heads).transpose(1, 2)
        
        # Manual causal self-attention to match NumPy exact behavior
        att = (q @ k.transpose(-2, -1)) * (1.0 / np.sqrt(k.size(-1)))
        mask = torch.tril(torch.ones(T, T, device=x.device)).view(1, 1, T, T)
        att = att.masked_fill(mask == 0, float('-inf'))
        att = torch.softmax(att, dim=-1)
        
        y = att @ v
        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.c_proj(y)

class TransformerBlock(nn.Module):
    def __init__(self, embed_dim, num_heads):
        super().__init__()
        self.ln_1 = nn.LayerNorm(embed_dim)
        self.attn = CausalSelfAttention(embed_dim, num_heads)
        self.ln_2 = nn.LayerNorm(embed_dim)
        self.mlp = nn.Sequential(
            nn.Linear(embed_dim, 4 * embed_dim),
            nn.GELU(),
            nn.Linear(4 * embed_dim, embed_dim)
        )
        # Rename mlp layers to match expectations of NumPy dict
        self.mlp[0].label = "c_fc"
        self.mlp[2].label = "c_proj"
        
    def forward(self, x):
        x = x + self.attn(self.ln_1(x))
        # Match sequential linear mapping logic
        h = self.ln_2(x)
        mlp_h = self.mlp[0](h)
        mlp_h = torch.relu(mlp_h) # GELU/ReLU approx
        x = x + self.mlp[2](mlp_h)
        return x

class DecisionTransformerModel(nn.Module):
    def __init__(self, state_dim=107, action_dim=8, embed_dim=128, max_timesteps=725, num_heads=4, num_layers=2):
        super().__init__()
        self.embed_state = nn.Linear(state_dim, embed_dim)
        self.embed_action = nn.Linear(action_dim, embed_dim)
        self.embed_return = nn.Linear(1, embed_dim)
        self.embed_timestep = nn.Embedding(max_timesteps, embed_dim)
        self.embed_ln = nn.LayerNorm(embed_dim)
        
        self.blocks = nn.ModuleList([TransformerBlock(embed_dim, num_heads) for _ in range(num_layers)])
        self.ln_f = nn.LayerNorm(embed_dim)
        self.predict_action = nn.Linear(embed_dim, action_dim)
        
    def forward(self, states, actions, returns_to_go, timesteps):
        B, T, _ = states.size()
        
        s_emb = self.embed_state(states)
        a_emb = self.embed_action(actions)
        r_emb = self.embed_return(returns_to_go)
        t_emb = self.embed_timestep(timesteps)
        
        # Interleave sequence: (R_1, s_1, a_1, R_2, s_2, a_2...)
        seq = torch.zeros((B, 3 * T, EMBED_DIM), device=states.device)
        seq[:, 0::3, :] = r_emb + t_emb
        seq[:, 1::3, :] = s_emb + t_emb
        seq[:, 2::3, :] = a_emb + t_emb
        
        x = self.embed_ln(seq)
        for block in self.blocks:
            x = block(x)
            
        x = self.ln_f(x)
        
        # We only predict action from state tokens (index 1::3)
        state_tokens = x[:, 1::3, :]
        logits = self.predict_action(state_tokens[:, -1, :])
        return logits

def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    dataset = TrajectoryDataset("parsed_trajectories.pkl", K=K)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    model = DecisionTransformerModel(embed_dim=EMBED_DIM, num_heads=NUM_HEADS, num_layers=NUM_LAYERS).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=LR)
    criterion = nn.CrossEntropyLoss()
    
    model.train()
    for epoch in range(EPOCHS):
        total_loss = 0
        correct = 0
        total = 0
        for s, a, r, t, target in dataloader:
            s, a, r, t, target = s.to(device), a.to(device), r.to(device), t.to(device), target.to(device)
            
            optimizer.zero_grad()
            logits = model(s, a, r, t)
            loss = criterion(logits, target)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item() * s.size(0)
            preds = torch.argmax(logits, dim=-1)
            correct += (preds == target).sum().item()
            total += target.size(0)
            
        epoch_loss = total_loss / total
        epoch_acc = correct / total
        print(f"Epoch {epoch+1}/{EPOCHS} - Loss: {epoch_loss:.4f} - Acc: {epoch_acc:.4f}")
        
    # Export weights to npz format matching the NumPy class keys
    weights = {}
    state_dict = model.state_dict()
    for k, v in state_dict.items():
        arr = v.cpu().numpy()
        # Rename blocks mlp linear layers specifically to match NumPy DecisionTransformer expects
        # blocks.0.mlp.0.weight -> blocks.0.mlp.c_fc.weight
        # blocks.0.mlp.2.weight -> blocks.0.mlp.c_proj.weight
        k_new = k
        if "mlp.0." in k_new:
            k_new = k_new.replace("mlp.0.", "mlp.c_fc.")
        elif "mlp.2." in k_new:
            k_new = k_new.replace("mlp.2.", "mlp.c_proj.")
        weights[k_new] = arr
        
    np.savez_compressed("rl_weights.npz", **weights)
    print("Saved model weights to rl_weights.npz successfully.")

if __name__ == "__main__":
    train()
