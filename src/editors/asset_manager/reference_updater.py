import os

class ReferenceUpdater:
    SCANNABLE_EXTS = {'.vmdl', '.vsmart', '.vmat', '.vpcf', '.vsndevts', '.vsnd', '.vmap'}

    def __init__(self, addon_content_path: str):
        self.addon_content_path = addon_content_path

    def _process_element_values(self, element, old_rel: str, new_rel: str) -> bool:
        """Recursively process all string values in an Element, replacing old_rel with new_rel."""
        modified = False
        try:
            keys = list(element.Keys)
        except Exception:
            return False

        for key in keys:
            try:
                val = element[key]
            except Exception:
                continue

            if isinstance(val, str) and old_rel in val:
                try:
                    element[key] = val.replace(old_rel, new_rel)
                    modified = True
                except Exception:
                    pass
            elif hasattr(val, 'Keys'):
                # Nested Element – recurse
                if self._process_element_values(val, old_rel, new_rel):
                    modified = True
            elif hasattr(val, 'Count') and hasattr(val, 'Item'):
                # Array/List attribute
                try:
                    for i in range(val.Count):
                        item_val = val[i]
                        if isinstance(item_val, str) and old_rel in item_val:
                            val[i] = item_val.replace(old_rel, new_rel)
                            modified = True
                        elif hasattr(item_val, 'Keys'):
                            if self._process_element_values(item_val, old_rel, new_rel):
                                modified = True
                except Exception:
                    pass

        return modified

    def _update_vmap_references(self, abs_path: str, old_rel: str, new_rel: str) -> bool:
        import tempfile
        import shutil

        dmx_model = None
        temp_path = None
        try:
            from src.dotnet import setup_keyvalues2
            Datamodel, Element, DeferredMode = setup_keyvalues2()

            # Load from a temporary copy so the original file is not locked
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.vmap', delete=False) as tmp:
                temp_path = tmp.name
                with open(abs_path, 'rb') as src:
                    shutil.copyfileobj(src, tmp)

            dmx_model = Datamodel.Load(temp_path, DeferredMode.Automatic)
            if not dmx_model:
                return False
                
            modified = False
            
            # Process PrefixAttributes (AttributeList – a Dictionary<string, object>)
            if hasattr(dmx_model, 'PrefixAttributes') and dmx_model.PrefixAttributes:
                try:
                    for key in list(dmx_model.PrefixAttributes.Keys):
                        val = dmx_model.PrefixAttributes[key]
                        if isinstance(val, str) and old_rel in val:
                            dmx_model.PrefixAttributes[key] = val.replace(old_rel, new_rel)
                            modified = True
                        elif hasattr(val, 'Count') and hasattr(val, 'Item'):
                            try:
                                for i in range(val.Count):
                                    item_val = val[i]
                                    if isinstance(item_val, str) and old_rel in item_val:
                                        val[i] = item_val.replace(old_rel, new_rel)
                                        modified = True
                            except Exception:
                                pass
                except Exception as e:
                    print(f"Warning: failed to process PrefixAttributes in {abs_path}: {e}")
            
            # Process AllElements (ElementList – iterates as DictionaryEntry)
            # Each DictionaryEntry.Value is the actual Element object
            if hasattr(dmx_model, 'AllElements') and dmx_model.AllElements:
                try:
                    for entry in dmx_model.AllElements:
                        element = entry.Value if hasattr(entry, 'Value') else entry
                        if self._process_element_values(element, old_rel, new_rel):
                            modified = True
                except Exception as e:
                    print(f"Warning: failed to process AllElements in {abs_path}: {e}")
            
            if modified:
                # Save to the original path (not locked since we loaded from temp)
                dmx_model.Save(abs_path, dmx_model.Encoding, dmx_model.EncodingVersion)
                
            if hasattr(dmx_model, 'Dispose'):
                dmx_model.Dispose()
            dmx_model = None
            import gc; gc.collect()
            
            return modified
        except Exception as e:
            print(f"Error updating vmap references via .NET in {abs_path}: {e}")
            return False
        finally:
            if dmx_model is not None:
                try:
                    if hasattr(dmx_model, 'Dispose'):
                        dmx_model.Dispose()
                except Exception:
                    pass
            if temp_path:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    def update_references(self, old_rel: str, new_rel: str) -> list[str]:
        modified = []
        old_rel = old_rel.replace('\\', '/')
        new_rel = new_rel.replace('\\', '/')
        for root, _, files in os.walk(self.addon_content_path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext not in self.SCANNABLE_EXTS:
                    continue
                abs_path = os.path.join(root, f)
                try:
                    if ext == '.vmap':
                        if self._update_vmap_references(abs_path, old_rel, new_rel):
                            modified.append(abs_path)
                    else:
                        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as file:
                            text = file.read()
                        if old_rel in text:
                            new_text = text.replace(old_rel, new_rel)
                            with open(abs_path, 'w', encoding='utf-8') as file:
                                file.write(new_text)
                            modified.append(abs_path)
                except Exception as e:
                    print(f"Error updating references in {abs_path}: {e}")
        return modified
