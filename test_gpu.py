# pyrefly: ignore [missing-import]
import torch

def test_gpu():
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")
    if cuda_available:
        device_count = torch.cuda.device_count()
        print(f"CUDA Device Count: {device_count}")
        for i in range(device_count):
            print(f"Device {i}: {torch.cuda.get_device_name(i)}")
            print(f"Device Capability: {torch.cuda.get_device_capability(i)}")
    else:
        print("CUDA is NOT available in this environment.")

if __name__ == "__main__":
    test_gpu()
