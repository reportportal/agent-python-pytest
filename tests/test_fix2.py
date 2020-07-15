item_parts = self._get_item_parts(item)
rp_name = self._add_item_hier_parts_other(item_parts, item, Module,
                                          hier_module, parts,
                                          rp_name)

"""for debug!!! in test_fix2.py"""

module_path = str(
    item.fspath.new(dirname=rp_name,
                    basename=part.fspath.basename,
                    drive=""))
rp_name = module_path if rp_name else module_path[1:]
print('======modulepath=======')
print(rp_name)
print(part.fspath.basename)
print(item.fspath)
print(module_path)
rp_name = module_path if rp_name else module_path[1:]
print(rp_name)

"""----end---"""