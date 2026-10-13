"""Generate the credential-free hosted widget bundle before Edge deployment."""
import json
from pathlib import Path
import sys
root = Path(__file__).resolve().parent.parent
bundle = {'protocol': 1, 'version': sys.argv[1], 'code': (root/'widgets/Arch-Labour-Remote.js').read_text()}
(root/'supabase/functions/arch-labour-widget/widget-bundle.mjs').write_text('// Generated from widgets/Arch-Labour-Remote.js. Do not include credentials.\nexport default '+json.dumps(bundle, ensure_ascii=False)+';\n')
