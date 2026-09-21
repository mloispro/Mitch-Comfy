"""Bounded native seed/dtype probes, not a search or production policy."""
import copy

HOUSE_REPORT_SHA='2f681509a799da00a38e4a40825ba0891c72110dc324e4863b47bc6ef791859c'


def validate_house_report_hash(manifest, actual):
    expected=manifest.get('baseline_report_sha256',HOUSE_REPORT_SHA).lower()
    if expected!=HOUSE_REPORT_SHA or actual.lower()!=HOUSE_REPORT_SHA:
        raise ValueError('Frozen house report changed or metadata contradicts its pin.')
    return HOUSE_REPORT_SHA


def changed_inputs(control, candidate):
    if set(control) != set(candidate):
        raise ValueError('Node set changed.')
    changes = []
    for key, node in control.items():
        other = candidate[key]
        if node.keys() != other.keys() or node['class_type'] != other['class_type']:
            raise ValueError('Node structure changed.')
        if set(node['inputs']) != set(other['inputs']):
            raise ValueError('Input set changed.')
        for field, value in node['inputs'].items():
            if value != other['inputs'][field]:
                changes.append(f'{key}.{field}')
        if {k:v for k,v in node.items() if k != 'inputs'} != {k:v for k,v in other.items() if k != 'inputs'}:
            raise ValueError('Node metadata changed.')
    return sorted(changes)


def build_probe(control, prefix):
    graph = copy.deepcopy(control)
    if graph['20']['class_type'] != 'RandomNoise' or graph['27']['class_type'] != 'SaveImage':
        raise ValueError('Expected audited native four-reference graph.')
    seed = graph['20']['inputs']['noise_seed']
    if type(seed) is not int or not 0 <= seed < 2**64-1:
        raise ValueError('Invalid seed.')
    if not prefix.startswith('upgrade-source-faithful/') or '..' in prefix or ':' in prefix:
        raise ValueError('Unsafe output prefix.')
    graph['20']['inputs']['noise_seed'] = seed + 1
    graph['27']['inputs']['filename_prefix'] = prefix
    if changed_inputs(control, graph) != ['20.noise_seed', '27.filename_prefix']:
        raise ValueError('Only the predeclared seed and destination may change.')
    return graph


def build_dtype_probe(control, prefix):
    if not prefix.startswith('upgrade-source-faithful/') or '..' in prefix or ':' in prefix:
        raise ValueError('Unsafe output prefix.')
    graph=copy.deepcopy(control)
    if (graph['1']['class_type']!='UNETLoader' or graph['1']['inputs']['weight_dtype']!='fp8_e4m3fn'
        or graph['27']['class_type']!='SaveImage'):
        raise ValueError('Expected the explicit FP8 diffusion-weight control.')
    graph['1']['inputs']['weight_dtype']='default'
    graph['27']['inputs']['filename_prefix']=prefix
    if changed_inputs(control,graph)!=['1.weight_dtype','27.filename_prefix']:
        raise ValueError('Only diffusion weight dtype and destination may change.')
    return graph


def precision_runtime_preflight(stats,minimum_ram_gib=24):
    flags=stats['system'].get('argv',[])
    forbidden=('--fp8_e4m3fn-unet','--fp8_e5m2-unet','--fp8_e8m0fnu-unet',
               '--fp16-unet','--fp32-unet','--fp64-unet')
    if any(flag in forbidden for flag in flags):
        raise ValueError('A process dtype override would invalidate this comparison.')
    available=stats['system']['ram_free']
    if available<minimum_ram_gib*1024**3:
        raise ValueError('Insufficient free host RAM for this larger-weight experiment.')
    if '3090' not in stats['devices'][0]['name']:
        raise ValueError('Precision probe remains locked to3090.')
    return {'ram_free_bytes':available,'minimum_ram_gib':minimum_ram_gib,
            'process_dtype_override_absent':True,'requested_diffusion_dtype':'default (expected BF16; verify log)',
            'text_encoder_unchanged':True}
