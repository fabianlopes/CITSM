import torch

print("GPU Disponível?", torch.cuda.is_available())
if torch.cuda.is_available():
    print("Nome da Placa:", torch.cuda.get_device_name(0))
    print("Memória VRAM:", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1), "GB")
else:
    print("❌ O Python ainda está usando a CPU.")