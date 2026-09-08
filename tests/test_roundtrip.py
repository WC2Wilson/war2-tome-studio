from pathlib import Path
import ast, struct, tempfile, importlib.util, sys
root=Path(__file__).parents[1]
ast.parse((root/"tome_workbench.py").read_text(encoding="utf-8"))
# Load without starting GUI.
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location("tome_workbench",root/"tome_workbench.py")
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)
# Synthetic archive: tag=25, 2 resources, base=1000, offsets after 16-byte header.
blob=struct.pack("<IHHII",25,2,1000,16,19)+b"abc"+b"defgh"
with tempfile.TemporaryDirectory() as td:
    p=Path(td)/"TOME.1"; p.write_bytes(blob)
    a=m.TomeArchive.load(p)
    assert a.base_id==1000 and a.resources==[b"abc",b"defgh"]
    out=Path(td)/"out"; a.save(out,backup=False)
    assert out.read_bytes()==blob
text=(root/"tome_workbench.py").read_text(encoding="utf-8")
assert "PSX" not in text and "PlayStation" not in text
print("TOME synthetic round-trip: PASS")
