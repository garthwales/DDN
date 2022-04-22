import torch
import torch.nn as nn

class PreNC(nn.Module):
    def __init__(self):
        super(PreNC, self).__init__()
        self.block1 = self.conv_block(c_in=1, c_out=128, kernel_size=3, stride=1, padding=1)
        self.block2 = self.conv_block(c_in=128, c_out=256, kernel_size=3, stride=1, padding=1)
        self.block3 = self.conv_block(c_in=256, c_out=512, kernel_size=3, stride=1, padding=1)
        self.lastcnn = nn.Conv2d(in_channels=512, out_channels=1024, kernel_size=3, stride=1, padding=1)
        self.relu = nn.ReLU()
        # self.maxpool = nn.MaxPool2d(kernel_size=2, stride=2)
        # self.fc = nn.Linear(out_features=10404)
    def forward(self, x):
        x = self.block1(x)
        # x = self.maxpool(x)
        x = self.block2(x)
        x = self.block3(x)
        # x = self.maxpool(x)
        x = self.relu(self.lastcnn(x))
        # combine the 1024 filters of 32x32 images into a singular 1024x1024 matrix (affinity matrix)
        x = x.view(x.size(0), 1, 1024, 1024)
        return x
    def conv_block(self, c_in, c_out, **kwargs):
        seq_block = nn.Sequential(
            nn.Conv2d(in_channels=c_in, out_channels=c_out, **kwargs),
            nn.BatchNorm2d(num_features=c_out),
            nn.ReLU()
            )
        return seq_block

class PostNC(nn.Module):
    def __init__(self):
        super(PostNC, self).__init__()
        self.block1 = self.conv_block(c_in=1, c_out=128, kernel_size=3, stride=1, padding=1)
        self.block2 = self.conv_block(c_in=128, c_out=256, kernel_size=3, stride=1, padding=1)
        self.lastcnn = nn.Conv2d(in_channels=256, out_channels=1, kernel_size=3, stride=1, padding=1)
    def forward(self, x):
        x = x.view(x.size(0), 1, 32, 32)
        x = self.block1(x)
        x = self.block2(x)
        x = self.lastcnn(x)
        x = torch.sigmoid(x)
        return x
    def conv_block(self, c_in, c_out, **kwargs):
        seq_block = nn.Sequential(
            nn.Conv2d(in_channels=c_in, out_channels=c_out, **kwargs),
            nn.BatchNorm2d(num_features=c_out),
            nn.ReLU()
            )
        return seq_block