from src.editors.asset_exporter.dependency_resolver import DependencyResolver
import sys
dr = DependencyResolver("D:/CG/Projects/Other/Hammer5Tools")
dr._visited.clear()
dr.missing_deps.clear()
print(dr.ASSET_DEPENDENCY_KEYS)
print("done")
