import torch
import tqdm
from pytorch_grad_cam.base_cam import BaseCAM


class ScoreCAM(BaseCAM):
    def __init__(
            self,
            model,
            target_layers,
            reshape_transform=None, 
            **kwargs):
        super(ScoreCAM, self).__init__(model,
                                       target_layers,
                                       reshape_transform=reshape_transform,
                                       uses_gradients=False, 
                                       **kwargs)

    def get_cam_weights(self,
                        input_tensor,
                        target_layer,
                        targets,
                        activations,
                        grads):
        with torch.no_grad():
            # upsample = torch.nn.UpsamplingBilinear2d(
            #     size=input_tensor.shape[-2:])
            upsample = torch.nn.Upsample(
                size=input_tensor[0].shape[-3:], mode="trilinear")  # input tensor is actually a list, and we have 3D case
            activation_tensor = torch.from_numpy(activations)
            activation_tensor = activation_tensor.to(self.device)

            upsampled = upsample(activation_tensor)

            maxs = upsampled.view(upsampled.size(0),
                                  upsampled.size(1), -1).max(dim=-1)[0]
            mins = upsampled.view(upsampled.size(0),
                                  upsampled.size(1), -1).min(dim=-1)[0]

            # maxs, mins = maxs[:, :, None, None], mins[:, :, None, None]
            maxs, mins = maxs[:, :, None, None, None], mins[:, :, None, None, None]  # for 3D
            upsampled = (upsampled - mins) / (maxs - mins + 1e-8)

            input_tensors = input_tensor[0][:, None,
                                         :, :] * upsampled[:, :, None, :, :]

            if hasattr(self, "batch_size"):
                BATCH_SIZE = self.batch_size
            else:
                # BATCH_SIZE = 16
                BATCH_SIZE = 1

            scores = []
            for target, tensor in zip(targets, input_tensors):
                for i in tqdm.tqdm(range(0, tensor.size(0), BATCH_SIZE)):
                    batch = tensor[i: i + BATCH_SIZE, :]
                    # outputs = [target(o).cpu().item()
                    #            for o in self.model(batch)]
                    outputs = [target(o).cpu().item()
                               for o in self.model([batch])]
                    scores.extend(outputs)
            scores = torch.Tensor(scores)
            scores = scores.view(activations.shape[0], activations.shape[1])
            weights = torch.nn.Softmax(dim=-1)(scores).numpy()
            return weights
