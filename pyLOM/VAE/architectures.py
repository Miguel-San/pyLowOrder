import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

## Encoder and decoder without a pooling operation
class Encoder2D(nn.Module):
    def __init__(self, nlayers, latent_dim, nx, ny, input_channels, filter_channels, kernel_size, padding, activation_funcs, nlinear, batch_norm=True, stride=2):
        super(Encoder2D, self).__init__()

        self.nlayers    = nlayers
        self.in_chan    = np.int(input_channels)
        self.filt_chan  = np.int(filter_channels)
        self._lat_dim   = np.int(latent_dim)
        self._nx        = np.int(nx)
        self._ny        = np.int(ny)
        self.funcs      = activation_funcs
        self.nlinear    = nlinear
        self.batch_norm = batch_norm

        # Create a list to hold the convolutional layers
        self.conv_layers = nn.ModuleList()
        self.norm_layers = nn.ModuleList()
        in_channels = self.in_chan # Initial input channels
        for ilayer in range(self.nlayers):
            out_channels = self.filt_chan * (1 << ilayer)  # Compute output channels
            conv_layer = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding)
            self.conv_layers.append(conv_layer)
            if self.batch_norm:
                self.norm_layers.append(nn.BatchNorm2d(out_channels))
            in_channels = out_channels  # Update in_channels for the next layer
       
        self.flat     = nn.Flatten()
        fc_input_size = out_channels * (self._nx // (1 << self.nlayers)) * (self._ny // (1 << self.nlayers))
        self.fc1      = nn.Linear(fc_input_size, self.nlinear)
        self.mu       = nn.Linear(self.nlinear, self._lat_dim)
        self.logvar   = nn.Linear(self.nlinear, self._lat_dim)

        self._reset_parameters()
    
    def _reset_parameters(self):
        for layer in self.modules():
            if isinstance(layer, nn.Conv2d):
                nn.init.xavier_uniform_(layer.weight)
            elif isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)

    def forward(self, x):        
        out = x
        for ilayer, conv_layer in enumerate(self.conv_layers):
            out = conv_layer(out)
            if self.batch_norm:
                out = self.norm_layers[ilayer](out)
            out = self.funcs[ilayer](out)
        out = self.funcs[ilayer+1](self.flat(out))
        out = self.funcs[ilayer+2](self.fc1(out))
        mu = self.mu(out)
        logvar = self.logvar(out)
        return mu, logvar
    
class Decoder2D(nn.Module):
    def __init__(self, nlayers, latent_dim, nx, ny, input_channels, filter_channels, kernel_size, padding, activation_funcs, nlinear, batch_norm=True, stride=2):
        super(Decoder2D, self).__init__()       
        
        self.nlayers    = nlayers
        self.filt_chan  = filter_channels
        self.in_chan    = input_channels
        self.lat_dim    = latent_dim
        self.nx         = nx
        self.ny         = ny
        self.funcs      = activation_funcs
        self.nlinear    = nlinear
        self.batch_norm = batch_norm

        self.fc1 = nn.Linear(in_features=self.lat_dim, out_features=self.nlinear)
        fc_output_size = int((self.filt_chan * (1 << (self.nlayers-1)) * self.nx // (1 << self.nlayers) * self.ny // (1 << self.nlayers)))
        self.fc2 = nn.Linear(in_features=self.nlinear, out_features=fc_output_size)

        # Create a list to hold the transposed convolutional layers
        self.deconv_layers = nn.ModuleList()
        self.norm_layers   = nn.ModuleList()
        in_channels = self.filt_chan * (1 << self.nlayers-1)
        for i in range(self.nlayers-1, 0, -1):
            out_channels = self.filt_chan * (1 << (i - 1))  # Compute output channels
            deconv_layer = nn.ConvTranspose2d(in_channels, out_channels, kernel_size, stride, padding)
            self.deconv_layers.append(deconv_layer)
            if self.batch_norm:
                self.norm_layers.append(nn.BatchNorm2d(in_channels))
            in_channels = out_channels  # Update in_channels for the next layer
        out_channels = self.in_chan
        deconv_layer = nn.ConvTranspose2d(in_channels, out_channels, kernel_size, stride, padding)
        self.deconv_layers.append(deconv_layer)
        if self.batch_norm:
            self.norm_layers.append(nn.BatchNorm2d(in_channels))

        self._reset_parameters()

    def _reset_parameters(self):
        for layer in self.modules():
            if isinstance(layer, nn.ConvTranspose2d):
                nn.init.xavier_uniform_(layer.weight)
            elif isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)

    def forward(self, x):
        out = self.funcs[self.nlayers+1](self.fc1(x))
        out = self.funcs[self.nlayers](self.fc2(out))
        out = out.view(out.size(0), self.filt_chan * (1 << (self.nlayers-1)), int(self.nx // (1 << self.nlayers)), int(self.ny // (1 << self.nlayers)))
        for ilayer, (deconv_layer) in enumerate(self.deconv_layers):
            if self.batch_norm:
                out = self.norm_layers[ilayer](out)
            out = self.funcs[self.nlayers-ilayer-1](deconv_layer(out))
        return out