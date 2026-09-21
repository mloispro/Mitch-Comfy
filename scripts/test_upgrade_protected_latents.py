"""CPU fixture: distinguish a protected person from changed background latents."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image
from safetensors.torch import save_file
import torch
import torch.nn.functional as F


class ProtectedLatentTest(unittest.TestCase):
    def test_background_change_is_not_reported_as_person_change(self):
        root=Path(__file__).resolve().parents[1]
        run=root/'work/upgrade-source-faithful-20260903/background-detail-house-scene-reference'
        manifest=json.loads((run/'experiment.json').read_text())
        graph=copy.deepcopy(manifest['prompt']);refs={r['name']:r for r in manifest['references']}
        for node in graph.values():
            if node['class_type']=='LoadImage':node['is_changed']=[refs[node['inputs']['image']]['sha256']]
        with Image.open(manifest['references'][2]['path']) as image:
            mask=torch.from_numpy(np.asarray(image.convert('L')).astype(np.float32)/255)[None,None]
        mapped=F.interpolate(mask,size=(48,80),mode='bilinear')
        source=torch.zeros((1,128,48,80));sampled=(mapped==1).float().expand_as(source).contiguous()
        with tempfile.TemporaryDirectory(prefix='latent-diagnostic-test-',dir=root/'work') as temporary:
            folder=Path(temporary)
            for name,value in (('source',source),('sampled',sampled)):
                save_file({'latent_tensor':value,'latent_format_version_0':torch.tensor([])},
                          str(folder/(name+'.latent')),metadata={'prompt':json.dumps(graph)})
            output=folder/'audit.json'
            result=subprocess.run([sys.executable,str(root/'scripts/evaluate-upgrade-protected-latents.py'),
                '--run',str(run),'--source-latent',str(folder/'source.latent'),
                '--sampled-latent',str(folder/'sampled.latent'),'--output',str(output)],
                capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            audit=json.loads(output.read_text())
            self.assertEqual(audit['all_black_mask_cells']['max_abs_error'],0)
            self.assertEqual(audit['person_core_64px']['exact_channel_vector_fraction'],1)
            self.assertEqual(audit['fully_editable_background_cells']['mean_abs_error'],1)


if __name__=='__main__':unittest.main()
