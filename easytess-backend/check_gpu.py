import torch
try:
    is_available = torch.cuda.is_available()
    print(f"CUDA available: {is_available}")
    if is_available:
        print(f"Device count: {torch.cuda.device_count()}")
        print(f"Device name: {torch.cuda.get_device_name(0)}")
    else:
        print("CUDA not available")
except Exception as e:
    print(f"Error checking CUDA: {e}")
