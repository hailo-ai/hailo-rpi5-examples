
"""
	"XFeat: Accelerated Features for Lightweight Image Matching, CVPR 2024."
	https://www.verlab.dcc.ufmg.br/descriptors/xfeat_cvpr24/
"""

import numpy as np
import os
import torch
import torch.nn.functional as F
import time
import onnxruntime as ort
from modules.hailo import Hailo
from hailo_platform import (FormatType)
from modules.model import *
from modules.interpolator import InterpolateSparse2d

class XFeat(nn.Module):
	""" 
		Implements the inference module for XFeat. 
		It supports inference for both sparse and semi-dense feature extraction & matching.
	"""

	def __init__(self, weights = os.path.abspath(os.path.dirname(__file__)) + '/../resources/xfeat.pt', top_k = 4096, width= 640,height=480, device= 'hailo'):
		super().__init__()
		self.dev = torch.device('cpu')
		self.net = XFeatModel().to(self.dev).eval()
		self.top_k = top_k
		self.sum = 0
		self.frames_num = 0

		self.device = device
		self.model_name = ''
		self.hef_path = ''
		if width == 640 and height == 480:
			hailo_model_name_480_640 = 'x_feature_13_without_pixel_unshuffle_normilize_softmax_slice_'
			hailo_model_name_480_640_path = 'resources/model_480_640/'
			self.model_name = hailo_model_name_480_640
			self.hef_path = hailo_model_name_480_640_path
		elif width == 320 and height == 224:
			hailo_model_name_224_320 = 'x_feature_13_without_pixel_unshuffle_normilize_softmax_slice_224_320_'
			hailo_model_name_224_320_path = 'resources/model_224_320/'
			self.model_name = hailo_model_name_224_320
			self.hef_path = hailo_model_name_224_320_path
		else:
			raise Exception("Sorry, wrong dimentions")
		self.hailo_model = Hailo(hef_path = f'{self.hef_path}{self.model_name}sim.hef',input_dtype=FormatType.FLOAT32, output_dtype=FormatType.FLOAT32)
		
		self.width = width
		self.height = height

		self.preprocess_onnx = False
		if self.preprocess_onnx:
			self.session = ort.InferenceSession(f'{self.hef_path}{self.model_name}only_head.onnx')
			self.onnx_input_names = [input.name for input in self.session.get_inputs()]
			self.onnx_output_names = [output.name for output in self.session.get_outputs()]
		self._nearest = InterpolateSparse2d('nearest')
		self._bilinear = InterpolateSparse2d('bilinear')
		if weights is not None:
			if isinstance(weights, str):
				print('loading weights from: ' + weights)
				state_dict = torch.load(weights, map_location=self.dev)
				state_dict['keypoint_head.0.layer.0.weight'] = state_dict['keypoint_head.0.layer.0.weight'].reshape(64,1,8,8)
				self.net.load_state_dict(state_dict)
			else:
				self.net.load_state_dict(weights)

		self.interpolator = InterpolateSparse2d('bilinear')
	
	def convert_to_onnx(self, x):
		name = 'x_feature_13_without_pixel_unshuffle_normilize_softmax_slice_224_320_test_model.onnx'
		torch.onnx.export(self.net,
		          args=(x),
		          f=f'./{name}',
		          input_names=['INPUT_1'],
		          output_names=['OUTPUT_1', 'OUTPUT_2', 'OUTPUT_3'],
		          verbose=True, 
		          export_params=True, 
		          training=torch.onnx.TrainingMode.PRESERVE, 
		          do_constant_folding=True,
		          opset_version=13)
		print(f'succsefuly exported to onnx named {name}')
		exit()
		
	def infer_onnx(self, x):
		input_names = [input.name for input in self.onnx_only_session.get_inputs()]
		output_names = [output.name for output in self.onnx_only_session.get_outputs()]
		net_input = {input_names[0]: x.numpy()}
		outputs = self.onnx_only_session.run(output_names, net_input)
		# return outputs
		return torch.from_numpy(outputs[0]), torch.from_numpy(outputs[1]), torch.from_numpy(outputs[2]) 
	
	def hailo_infer_per(self, x):
		if self.preprocess_onnx:
			onnx_output = self.session.run(self.onnx_output_names, {self.onnx_input_names[0]: x.numpy()})
			x = onnx_output[0]
		else:
			x = x.mean(dim=1, keepdim = True)
			x = nn.InstanceNorm2d(1)(x).numpy()
		infer_results = self.hailo_model.infer(np.transpose(x,(0, 2, 3, 1)))
		OUTPUT_1 = infer_results[f'{self.model_name}sim/slice1']
		OUTPUT_2 = infer_results[f'{self.model_name}sim/ew_mult1']
		OUTPUT_3 = infer_results[f'{self.model_name}sim/conv27']
		return torch.Tensor(np.transpose(OUTPUT_2,(0,3,1,2))), OUTPUT_1, torch.Tensor(np.transpose(OUTPUT_3,(0,3,1,2)))


	@torch.inference_mode()
	def detectAndCompute(self, x, top_k = None):
		"""
			Compute sparse keypoints & descriptors. Supports batched mode.

			input:
				x -> torch.Tensor(B, C, H, W): grayscale or rgb image
				top_k -> int: keep best k features
			return:
				List[Dict]: 
					'keypoints'    ->   torch.Tensor(N, 2): keypoints (x,y)
					'scores'       ->   torch.Tensor(N,): keypoint scores
					'descriptors'  ->   torch.Tensor(N, 64): local features
		"""
		if top_k is None: top_k = self.top_k
		x, rh1, rw1 = self.preprocess_tensor(x)
		
		B, _, _H1, _W1 = x.shape

		if x.shape[2] != self.height or x.shape[3] != self.width:
			raise Exception("Error: retreat model size must be the same as record model size")
		# self.convert_to_onnx(x)
		if self.device == 'torch':
			M1, K1, H1 = self.net(x)
		elif self.device == 'hailo':
			# start = time.time()
			M1, K1, H1 = self.hailo_infer_per(x)
			# end = time.time()
			# print("preprocess+hailo ",end-start)
		elif self.device == 'onnx':
			M1, K1, H1 = self.infer_onnx(x)


		start = time.time()
		if self.device == 'hailo':
			B, H, W, _= K1.shape
			K1h = K1.reshape(B, H, W, 8, 8).transpose(0, 3, 1, 4, 2).reshape(B, 1, H * 8, W * 8)
		elif self.device == 'torch':
			K1h = self.get_kpts_heatmap(K1)
		elif self.device == 'onnx':
			K1h = self.get_kpts_heatmap(K1)
		K1h = torch.Tensor(K1h)
		mkpts = self.NMS(K1h, threshold=0.05, kernel_size=5)
		#Compute reliability scores

		scores = (self._nearest(K1h, mkpts, _H1, _W1) * self._bilinear(H1, mkpts, _H1, _W1)).squeeze(-1)
		scores[torch.all(mkpts == 0, dim=-1)] = -1

		#Select top-k features
		idxs = torch.argsort(-scores)
		mkpts_x  = torch.gather(mkpts[...,0], -1, idxs)[:, :top_k]
		mkpts_y  = torch.gather(mkpts[...,1], -1, idxs)[:, :top_k]
		mkpts = torch.cat([mkpts_x[...,None], mkpts_y[...,None]], dim=-1)
		scores = torch.gather(scores, -1, idxs)[:, :top_k]

		#Interpolate descriptors at kpts positions
		feats = self.interpolator(M1, mkpts, H = _H1, W = _W1)
		#L2-Normalize
		feats = F.normalize(feats, dim=-1)

		#Correct kpt scale
		mkpts = mkpts * torch.tensor([rw1,rh1], device=mkpts.device).view(1, 1, -1)

		valid = scores > 0

		end = time.time()
		self.frames_num = self.frames_num + 1
		self.sum = self.sum + end-start
		# print(self.sum)
		# print(self.frames_num)
		print("post process ",self.sum/self.frames_num)
		return [  
				   {'keypoints': mkpts[b][valid[b]],
					'scores': scores[b][valid[b]],
					'descriptors': feats[b][valid[b]]} for b in range(B) 
			   ]

	@torch.inference_mode()
	def detectAndComputeDense(self, x, top_k = None, multiscale = True):
		"""
			Compute dense *and coarse* descriptors. Supports batched mode.

			input:
				x -> torch.Tensor(B, C, H, W): grayscale or rgb image
				top_k -> int: keep best k features
			return: features sorted by their reliability score -- from most to least
				List[Dict]: 
					'keypoints'    ->   torch.Tensor(top_k, 2): coarse keypoints
					'scales'       ->   torch.Tensor(top_k,): extraction scale
					'descriptors'  ->   torch.Tensor(top_k, 64): coarse local features
		"""
		if top_k is None: top_k = self.top_k
		if multiscale:
			mkpts, sc, feats = self.extract_dualscale(x, top_k)
		else:
			mkpts, feats = self.extractDense(x, top_k)
			sc = torch.ones(mkpts.shape[:2], device=mkpts.device)

		return {'keypoints': mkpts,
				'descriptors': feats,
				'scales': sc }

	@torch.inference_mode()
	def match_xfeat(self, img1, img2, top_k = None, min_cossim = -1):
		"""
			Simple extractor and MNN matcher.
			For simplicity it does not support batched mode due to possibly different number of kpts.
			input:
				img1 -> torch.Tensor (1,C,H,W) or np.ndarray (H,W,C): grayscale or rgb image.
				img2 -> torch.Tensor (1,C,H,W) or np.ndarray (H,W,C): grayscale or rgb image.
				top_k -> int: keep best k features
			returns:
				mkpts_0, mkpts_1 -> np.ndarray (N,2) xy coordinate matches from image1 to image2
		"""
		if top_k is None: top_k = self.top_k
		img1 = self.parse_input(img1)
		img2 = self.parse_input(img2)

		out1 = self.detectAndCompute(img1, top_k=top_k)[0]
		out2 = self.detectAndCompute(img2, top_k=top_k)[0]

		idxs0, idxs1 = self.match(out1['descriptors'], out2['descriptors'], min_cossim=min_cossim )

		return out1['keypoints'][idxs0].cpu().numpy(), out2['keypoints'][idxs1].cpu().numpy()

	@torch.inference_mode()
	def match_xfeat_star(self, im_set1, im_set2, top_k = None):
		"""
			Extracts coarse feats, then match pairs and finally refine matches, currently supports batched mode.
			input:
				im_set1 -> torch.Tensor(B, C, H, W) or np.ndarray (H,W,C): grayscale or rgb images.
				im_set2 -> torch.Tensor(B, C, H, W) or np.ndarray (H,W,C): grayscale or rgb images.
				top_k -> int: keep best k features
			returns:
				matches -> List[torch.Tensor(N, 4)]: List of size B containing tensor of pairwise matches (x1,y1,x2,y2)
		"""
		if top_k is None: top_k = self.top_k
		im_set1 = self.parse_input(im_set1)
		im_set2 = self.parse_input(im_set2)

		#Compute coarse feats
		out1 = self.detectAndComputeDense(im_set1, top_k=top_k)
		out2 = self.detectAndComputeDense(im_set2, top_k=top_k)

		#Match batches of pairs
		idxs_list = self.batch_match(out1['descriptors'], out2['descriptors'] )
		B = len(im_set1)

		#Refine coarse matches
		#this part is harder to batch, currently iterate
		matches = []
		for b in range(B):
			matches.append(self.refine_matches(out1, out2, matches = idxs_list, batch_idx=b))

		return matches if B > 1 else (matches[0][:, :2].cpu().numpy(), matches[0][:, 2:].cpu().numpy())

	def preprocess_tensor(self, x):
		""" Guarantee that image is divisible by 32 to avoid aliasing artifacts. """
		if isinstance(x, np.ndarray) and x.shape == 3:
			x = torch.tensor(x).permute(2,0,1)[None]
		x = x.to(self.dev).float()

		H, W = x.shape[-2:]
		_H, _W = (H//32) * 32, (W//32) * 32
		rh, rw = H/_H, W/_W

		x = F.interpolate(x, (_H, _W), mode='bilinear', align_corners=False)
		return x, rh, rw

	def get_kpts_heatmap(self, x):
		# scores = F.softmax(kpts*softmax_temp, 1)[:, :64]
		B, _, H, W = x.shape
		heatmap = x.permute(0, 2, 3, 1).reshape(B, H, W, 8, 8)
		heatmap = heatmap.permute(0, 1, 3, 2, 4).reshape(B, 1, H*8, W*8)
		return heatmap
	
	def NMS(self, x, threshold = 0.05, kernel_size = 5):
		B = x.shape[0]
		pad=kernel_size//2
		local_max = nn.MaxPool2d(kernel_size=kernel_size, stride=1, padding=pad)(x)
		
		pos = np.logical_and(x == local_max, x > threshold)

		pos_batched = [k.nonzero()[..., 1:].flip(-1) for k in pos]

		pad_val = max([len(x) for x in pos_batched])
		pos = torch.zeros((B, pad_val, 2), dtype=torch.long, device=x.device)

		#Pad kpts and build (B, N, 2) tensor
		for b in range(len(pos_batched)):
			pos[b, :len(pos_batched[b]), :] = pos_batched[b]

		return pos

	@torch.inference_mode()
	def batch_match(self, feats1, feats2, min_cossim = -1):
		B = len(feats1)
		cossim = torch.bmm(feats1, feats2.permute(0,2,1))
		match12 = torch.argmax(cossim, dim=-1)
		match21 = torch.argmax(cossim.permute(0,2,1), dim=-1)

		idx0 = torch.arange(len(match12[0]), device=match12.device)

		batched_matches = []

		for b in range(B):
			mutual = match21[b][match12[b]] == idx0

			if min_cossim > 0:
				cossim_max, _ = cossim[b].max(dim=1)
				good = cossim_max > min_cossim
				idx0_b = idx0[mutual & good]
				idx1_b = match12[b][mutual & good]
			else:
				idx0_b = idx0[mutual]
				idx1_b = match12[b][mutual]

			batched_matches.append((idx0_b, idx1_b))

		return batched_matches

	def subpix_softmax2d(self, heatmaps, temp = 3):
		N, H, W = heatmaps.shape
		heatmaps = torch.softmax(temp * heatmaps.view(-1, H*W), -1).view(-1, H, W)
		x, y = torch.meshgrid(torch.arange(W, device =  heatmaps.device ), torch.arange(H, device =  heatmaps.device ), indexing = 'xy')
		x = x - (W//2)
		y = y - (H//2)

		coords_x = (x[None, ...] * heatmaps)
		coords_y = (y[None, ...] * heatmaps)
		coords = torch.cat([coords_x[..., None], coords_y[..., None]], -1).view(N, H*W, 2)
		coords = coords.sum(1)

		return coords

	def refine_matches(self, d0, d1, matches, batch_idx, fine_conf = 0.25):
		idx0, idx1 = matches[batch_idx]
		feats1 = d0['descriptors'][batch_idx][idx0]
		feats2 = d1['descriptors'][batch_idx][idx1]
		mkpts_0 = d0['keypoints'][batch_idx][idx0]
		mkpts_1 = d1['keypoints'][batch_idx][idx1]
		sc0 = d0['scales'][batch_idx][idx0]

		#Compute fine offsets
		offsets = self.net.fine_matcher(torch.cat([feats1, feats2],dim=-1))
		conf = F.softmax(offsets*3, dim=-1).max(dim=-1)[0]
		offsets = self.subpix_softmax2d(offsets.view(-1,8,8))

		mkpts_0 += offsets* (sc0[:,None]) #*0.9 #* (sc0[:,None])

		mask_good = conf > fine_conf
		mkpts_0 = mkpts_0[mask_good]
		mkpts_1 = mkpts_1[mask_good]

		return torch.cat([mkpts_0, mkpts_1], dim=-1)

	@torch.inference_mode()
	def match(self, feats1, feats2, min_cossim = 0.82):

		cossim = feats1 @ feats2.t()
		cossim_t = feats2 @ feats1.t()
		
		_, match12 = cossim.max(dim=1)
		_, match21 = cossim_t.max(dim=1)

		idx0 = torch.arange(len(match12), device=match12.device)
		mutual = match21[match12] == idx0

		if min_cossim > 0:
			cossim, _ = cossim.max(dim=1)
			good = cossim > min_cossim
			idx0 = idx0[mutual & good]
			idx1 = match12[mutual & good]
		else:
			idx0 = idx0[mutual]
			idx1 = match12[mutual]

		return idx0, idx1

	def create_xy(self, h, w, dev):
		y, x = torch.meshgrid(torch.arange(h, device = dev), 
								torch.arange(w, device = dev), indexing='ij')
		xy = torch.cat([x[..., None],y[..., None]], -1).reshape(-1,2)
		return xy

	def extractDense(self, x, top_k = 8_000):
		if top_k < 1:
			top_k = 100_000_000

		x, rh1, rw1 = self.preprocess_tensor(x)

		M1, K1, H1 = self.net(x)
		
		B, C, _H1, _W1 = M1.shape
		
		xy1 = (self.create_xy(_H1, _W1, M1.device) * 8).expand(B,-1,-1)

		M1 = M1.permute(0,2,3,1).reshape(B, -1, C)
		H1 = H1.permute(0,2,3,1).reshape(B, -1)

		_, top_k = torch.topk(H1, k = min(len(H1[0]), top_k), dim=-1)

		feats = torch.gather( M1, 1, top_k[...,None].expand(-1, -1, 64))
		mkpts = torch.gather(xy1, 1, top_k[...,None].expand(-1, -1, 2))
		mkpts = mkpts * torch.tensor([rw1, rh1], device=mkpts.device).view(1,-1)

		return mkpts, feats

	def extract_dualscale(self, x, top_k, s1 = 0.6, s2 = 1.3):
		x1 = F.interpolate(x, scale_factor=s1, align_corners=False, mode='bilinear')
		x2 = F.interpolate(x, scale_factor=s2, align_corners=False, mode='bilinear')

		B, _, _, _ = x.shape

		mkpts_1, feats_1 = self.extractDense(x1, int(top_k*0.20))
		mkpts_2, feats_2 = self.extractDense(x2, int(top_k*0.80))

		mkpts = torch.cat([mkpts_1/s1, mkpts_2/s2], dim=1)
		sc1 = torch.ones(mkpts_1.shape[:2], device=mkpts_1.device) * (1/s1)
		sc2 = torch.ones(mkpts_2.shape[:2], device=mkpts_2.device) * (1/s2)
		sc = torch.cat([sc1, sc2],dim=1)
		feats = torch.cat([feats_1, feats_2], dim=1)

		return mkpts, sc, feats

	def parse_input(self, x):
		if len(x.shape) == 3:
			x = x[None, ...]

		if isinstance(x, np.ndarray):
			x = torch.tensor(x).permute(0,3,1,2)/255

		return x
