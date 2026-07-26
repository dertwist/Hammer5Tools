import os
import re

class ReferenceUpdater:
    SCANNABLE_EXTS = {'.vmdl', '.vsmart', '.vmat', '.vpcf', '.vsndevts', '.vsnd', '.vmap', '.vpost', '.vanim', '.vseq', '.vphys'}

    def __init__(self, addon_content_path: str):
        self.addon_content_path = addon_content_path

    @staticmethod
    def _compile(renames: dict):
        """One alternation over every old path, longest first.

        Longest-first so a path that is a prefix of another cannot shadow it, and
        a single pass rather than chained str.replace calls so a rename whose
        *output* matches another rename's input can't be applied twice.
        """
        keys = sorted(renames, key=len, reverse=True)
        if not keys:
            return None, {}
        return re.compile('|'.join(re.escape(k) for k in keys)), renames

    def _apply(self, text: str, pattern, renames: dict) -> str:
        return pattern.sub(lambda m: renames[m.group(0)], text)

    def _process_element_values(self, element, pattern, renames: dict) -> bool:
        """Recursively rewrite every string value in an Element."""
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

            if isinstance(val, str):
                new = self._apply(val, pattern, renames)
                if new != val:
                    try:
                        element[key] = new
                        modified = True
                    except Exception:
                        pass
            elif hasattr(val, 'Keys'):
                # Nested Element – recurse
                if self._process_element_values(val, pattern, renames):
                    modified = True
            elif hasattr(val, 'Count') and hasattr(val, 'Item'):
                # Array/List attribute
                try:
                    for i in range(val.Count):
                        item_val = val[i]
                        if isinstance(item_val, str):
                            new = self._apply(item_val, pattern, renames)
                            if new != item_val:
                                val[i] = new
                                modified = True
                        elif hasattr(item_val, 'Keys'):
                            if self._process_element_values(item_val, pattern, renames):
                                modified = True
                except Exception:
                    pass

        return modified

    def _rewrite_prefix(self, abs_path: str, pattern, renames: dict) -> bool:
        """Repoint the paths in the DMX prefix block's asset-reference cache.

        Datamodel.NET exposes only part of that region as writable attributes, so
        renames applied through the object model leave the cache holding the old
        paths and Hammer reports every moved asset as missing even though the map
        body is correct. This rewrites the region's strings directly.
        """
        try:
            from src.gitvmapmerge import rewrite_prefix_strings
            with open(abs_path, 'rb') as f:
                buf = f.read()
            out = rewrite_prefix_strings(buf, lambda s: self._apply(s, pattern, renames))
            if out is None:
                print(f"Warning: could not rewrite prefix asset cache in {abs_path}")
                return False
            if out != buf:
                with open(abs_path, 'wb') as f:
                    f.write(out)
                return True
        except Exception as e:
            print(f"Warning: prefix asset cache rewrite failed for {abs_path}: {e}")
        return False

    def _update_vmap_references(self, abs_path: str, pattern, renames: dict) -> bool:
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
            prefix_touched = False
            if hasattr(dmx_model, 'PrefixAttributes') and dmx_model.PrefixAttributes:
                try:
                    for key in list(dmx_model.PrefixAttributes.Keys):
                        val = dmx_model.PrefixAttributes[key]
                        if isinstance(val, str):
                            new = self._apply(val, pattern, renames)
                            if new != val:
                                dmx_model.PrefixAttributes[key] = new
                                modified = prefix_touched = True
                        elif hasattr(val, 'Count') and hasattr(val, 'Item'):
                            try:
                                for i in range(val.Count):
                                    item_val = val[i]
                                    if isinstance(item_val, str):
                                        new = self._apply(item_val, pattern, renames)
                                        if new != item_val:
                                            val[i] = new
                                            modified = prefix_touched = True
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
                        if self._process_element_values(element, pattern, renames):
                            modified = True
                except Exception as e:
                    print(f"Warning: failed to process AllElements in {abs_path}: {e}")

            if modified:
                # Save to the original path (not locked since we loaded from temp)
                dmx_model.Save(abs_path, dmx_model.Encoding, dmx_model.EncodingVersion)
                # Datamodel.NET's binary writer drops the DMX prefix-attribute block,
                # which holds the map thumbnail and the asset-reference cache. Splice
                # the original's back unless we just rewrote paths inside it, in which
                # case the freshly written one is the correct version.
                if not prefix_touched:
                    try:
                        from src.gitvmapmerge import _splice_prefix
                        _splice_prefix(temp_path, abs_path)
                    except Exception as e:
                        print(f"Warning: could not restore prefix block in {abs_path}: {e}")

            if hasattr(dmx_model, 'Dispose'):
                dmx_model.Dispose()
            dmx_model = None
            import gc; gc.collect()

            # Not gated on `modified`: the body and the prefix cache can hold
            # stale paths independently, and after a body-only rewrite the cache
            # is the only thing left pointing at the old locations.
            if self._rewrite_prefix(abs_path, pattern, renames):
                modified = True

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
        """Single rename. Prefer update_references_batch when moving more than one
        file: this walks the whole addon and reloads every vmap per call."""
        return self.update_references_batch({old_rel: new_rel})

    def update_references_batch(self, renames: dict) -> list[str]:
        """Apply many renames in one pass.

        A per-file loop costs one full addon walk and one DMX load/save of every
        map for each file moved, which does not finish on a real asset library -
        reorganising a few hundred props is thousands of reloads of a map that
        may be tens of MB. Here every path is rewritten in a single visit.
        """
        renames = {k.replace('\\', '/'): v.replace('\\', '/') for k, v in renames.items()}
        pattern, renames = self._compile(renames)
        if pattern is None:
            return []

        modified = []
        for root, _, files in os.walk(self.addon_content_path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext not in self.SCANNABLE_EXTS:
                    continue
                abs_path = os.path.join(root, f)
                try:
                    if ext == '.vmap':
                        if self._update_vmap_references(abs_path, pattern, renames):
                            modified.append(abs_path)
                    else:
                        with open(abs_path, 'r', encoding='utf-8', errors='ignore', newline='') as file:
                            text = file.read()
                        new_text = self._apply(text, pattern, renames)
                        if new_text != text:
                            with open(abs_path, 'w', encoding='utf-8', newline='') as file:
                                file.write(new_text)
                            modified.append(abs_path)
                except Exception as e:
                    print(f"Error updating references in {abs_path}: {e}")
        return modified
