# Copyright (c) 2021-2022, InterDigital Communications, Inc
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted (subject to the limitations in the disclaimer
# below) provided that the following conditions are met:

# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name of InterDigital Communications, Inc nor the names of its
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.

# NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY
# THIS LICENSE. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from pathlib import Path

from PIL import Image
from torch.utils.data import Dataset
import numpy as np
from torch import from_numpy
from os import path
from compressai.registry import register_dataset
from torchvision.transforms import transforms
from torch.nn.functional import interpolate
import torch
import math
from compressai.datasets import tiling

@register_dataset("ImageFolder")
class ImageFolder(Dataset):
    """Load an image folder database. Training and testing image samples
    are respectively stored in separate directories:

    .. code-block::

        - rootdir/
            - train/
                - img000.png
                - img001.png
            - test/
                - img000.png
                - img001.png

    Args:
        root (string): root directory of the dataset
        transform (callable, optional): a function or transform that takes in a
            PIL image and returns a transformed version
        split (string): split mode ('train' or 'val')
    """

    def __init__(self, root, transform=None, split="train"):
        splitdir = Path(root) / split

        if not splitdir.is_dir():
            raise RuntimeError(f'Invalid directory "{root}"')

        self.samples = [f for f in splitdir.iterdir() if f.is_file()]

        self.transform = transform

    def __getitem__(self, index):
        """
        Args:
            index (int): Index

        Returns:
            img: `PIL.Image.Image` or transformed `PIL.Image.Image`.
        """
        img = Image.open(self.samples[index]).convert("RGB")
        # print(img)
        if self.transform:
            return self.transform(img)
        return img

    def __len__(self):
        return len(self.samples)


@register_dataset("FeatureFolderTest")
class FeatureFolderTest(Dataset):

    def __init__(self, root, split="test"):
        splitdir = Path(root) / split

        if not splitdir.is_dir():
            raise RuntimeError(f'Invalid directory "{root}"')

        self.samples = [f for f in Path(root).iterdir() if (f.is_file() and f.stem[1] != '6')]
        
    def __getitem__(self, index):
        """
        Args:
            index (int): Index

        Returns:
            img: `PIL.Image.Image` or transformed `PIL.Image.Image`.
        """
        fmap = from_numpy(np.load(self.samples[index]))
        head_tail = path.split(self.samples[index])
        return fmap, head_tail[1]

    def __len__(self):
        return len(self.samples)


@register_dataset("FeatureFolder256_to4")
class FeatureFolder256_to4(Dataset):
    """Load an feature map folder database. 

    Args:
        root (string): root directory of the dataset
        split (string): split mode ('train' or 'val')
    """

    def __init__(self, root, split="train"):
        splitdir = Path(root) / split

        if not splitdir.is_dir():
            raise RuntimeError(f'Invalid directory "{root}"')

        self.samples = [f for f in splitdir.iterdir() if (f.is_file() and f.stem[1] != '6')]
        

    def __getitem__(self, index):
        """
        Args:
            index (int): Index

        Returns:
            t (Tensor), path.split (String):
                4-channel feature map, filename of the feature map
        """
        t = torch.as_tensor(np.load(self.samples[index], allow_pickle=True).astype('float'))
        
        if 128 < max(t.shape[2], t.shape[3]) <= 256:    # p2
            hpad, wpad = 256-t.shape[2], 256-t.shape[3]
        elif 64 < max(t.shape[2], t.shape[3]) <= 128:     # p3
            hpad, wpad = 128-t.shape[2], 128-t.shape[3]
        elif 32 < max(t.shape[2], t.shape[3]) <= 64:    # p4
            hpad, wpad = 64-t.shape[2], 64-t.shape[3]
        elif max(t.shape[2], t.shape[3]) <= 32:         # p5
            hpad, wpad = 32-t.shape[2], 32-t.shape[3]

        padding = torch.nn.ZeroPad2d((math.ceil(wpad/2),math.floor(wpad/2), math.ceil(hpad/2), math.floor(hpad/2)))
        # 1, 256, 256, 256
        t = padding(t)
        t = tiling.tile_256_to_4_torch(t.squeeze(0)).unsqueeze(0) # 1, 4, 16h, 16w

        if self.samples[index].stem[1] == '2':   # p2
            t = interpolate(t, scale_factor=0.5, mode='bicubic')
        
        return t.float(), path.split(self.samples[index])[1]
        
    def __len__(self):
        return len(self.samples)


@register_dataset("FeatureFolderScale")
class FeatureFolderScale(Dataset):
    """Load an image folder database. Training and testing image samples
    are respectively stored in separate directories:

    Args:
        root (string): root directory of the dataset
        transform (callable, optional): a function or transform that takes in a
            PIL image and returns a transformed version
        split (string): split mode ('train' or 'val')
    """

    def __init__(self, root, split="train"):
        splitdir = Path(root) / split

        if not splitdir.is_dir():
            raise RuntimeError(f'Invalid directory "{root}"')

        self.samples = [f for f in splitdir.iterdir() if f.is_file()]

    def __getitem__(self, index):
        """
        Args:
            index (int): Index

        Returns:
            img: `PIL.Image.Image` or transformed `PIL.Image.Image`.
        """
        t = torch.as_tensor(np.load(self.samples[index], allow_pickle=True).astype('float')).unsqueeze(0)
        if self.samples[index].stem[1] == '2':   # p2
            t = interpolate(t, scale_factor=0.5, mode='bicubic')
        
        return t.float()

    def __len__(self):
        return len(self.samples)

@register_dataset("FeatureFolderTiledNorm")
class FeatureFolderTiledNorm(Dataset):
    #FeatureMaps scaled & normalized
    """Load an image folder database. Training and testing image samples
    are respectively stored in separate directories:

    Args:
        root (string): root directory of the dataset
        transform (callable, optional): a function or transform that takes in a
            PIL image and returns a transformed version
        split (string): split mode ('train' or 'val')
    """

    def __init__(self, root, split="train"):
        splitdir = Path(root) / split

        if not splitdir.is_dir():
            raise RuntimeError(f'Invalid directory "{root}"')

        self.samples = [f for f in splitdir.iterdir() if f.is_file()]
        #self.norm = transforms.Normalize(mean, std)    

    def __getitem__(self, index):
        
        
        t = torch.as_tensor(np.load(self.samples[index], allow_pickle=True).astype('float')).unsqueeze(0).unsqueeze(0)
        
       # t = from_numpy(load(self.samples[index], allow_pickle=True))
        if self.samples[index].stem[1] == '2':   # p2
            t = interpolate(t, scale_factor=0.5, mode='bicubic')
        t = torch.clamp(t, min=-26.426828384399414, max=28.397470474243164)
        t = (t+26.426828384399414)/54.824298858642578
        t = torch.clamp(t, 0, 1)
        # normalize
        # scaling
        
        return t.float()

    def __len__(self):
        return len(self.samples)




@register_dataset("FeatureFolderNorm")
class FeatureFolderNorm(Dataset):
    #FeatureMaps scaled & normalized
    """Load an image folder database. Training and testing image samples
    are respectively stored in separate directories:

    Args:
        root (string): root directory of the dataset
        transform (callable, optional): a function or transform that takes in a
            PIL image and returns a transformed version
        split (string): split mode ('train' or 'val')
    """

    def __init__(self, root, split="train"):
        splitdir = Path(root) / split

        if not splitdir.is_dir():
            raise RuntimeError(f'Invalid directory "{root}"')

        self.samples = [f for f in splitdir.iterdir() if f.is_file()]
        #self.norm = transforms.Normalize(mean, std)    

    def __getitem__(self, index):
        """
        Args:
            index (int): Index

        Returns:
            img: `PIL.Image.Image` or transformed `PIL.Image.Image`.
        """
        t = torch.as_tensor(np.load(self.samples[index], allow_pickle=True).astype('float'))
       # t = from_numpy(load(self.samples[index], allow_pickle=True))
        t = torch.clamp(t, min=-26.426828384399414, max=28.397470474243164)
        t = (t+26.426828384399414)/54.824298858642578
        # normalize
        # scaling
        if t.shape[2] == 256 and t.shape[3] == 256:
            return t.float()
        if 64 < max(t.shape[2], t.shape[3]) <= 128:     # p3
            t = interpolate(t, scale_factor=2, mode='bicubic')
        elif 32 < max(t.shape[2], t.shape[3]) <= 64:    # p4
            t = interpolate(t, scale_factor=4, mode='bicubic')
        elif max(t.shape[2], t.shape[3]) <= 32:         # p5
            t = interpolate(t, scale_factor=8, mode='bicubic')

        hpad, wpad = 256-t.shape[2], 256-t.shape[3]
        padding = torch.nn.ReplicationPad2d((math.ceil(wpad/2),math.floor(wpad/2), math.ceil(hpad/2), math.floor(hpad/2)))
        
        if torch.max(t) > 1 or torch.min(t) < 0:
            print("!!!!!!!!!! ERROR !!!!!!!!")
            print(self.samples[index])
      
        return padding(t).type(torch.FloatTensor)
        #print("x_hat: {}".format(x_hat[0, 1, 0, 0]))

        #return from_numpy(load(self.samples[index]))
        # img = Image.open(self.samples[index]).convert("RGB")
        # if self.transform:
        #     return self.transform(img)
        # return img

    def __len__(self):
        return len(self.samples)


@register_dataset("FeatureFolderGeneral")
class FeatureFolderGeneral(Dataset):

    def __init__(self, root, split="test"):
        splitdir = Path(root) / split
        if not splitdir.is_dir():
            raise RuntimeError(f'Invalid directory "{root}"')

        self.samples = [f for f in splitdir.iterdir() if f.is_file() and f.stem[0] == 'p']
        
    def __getitem__(self, index):
        """
        Args:
            index (int): Index

        Returns:
            x (Tensor): Feature Map (1, 256, 256, 256)
        """
        x = from_numpy(np.load(self.samples[index]))
        filename = path.split(self.samples[index])
        if filename[1][1] == '3':
            x = interpolate(x, scale_factor=2, mode='bicubic')
        if filename[1][1] == '4':
            x = interpolate(x, scale_factor=4, mode='bicubic')
        if filename[1][1] == '5':
            x = interpolate(x, scale_factor=8, mode='bicubic')

        hpad, wpad = 256-x.shape[2], 256-x.shape[3]
        padding = torch.nn.ZeroPad2d((math.ceil(wpad/2),math.floor(wpad/2), math.ceil(hpad/2), math.floor(hpad/2)))
        return padding(x)

    def __len__(self):
        return len(self.samples)


