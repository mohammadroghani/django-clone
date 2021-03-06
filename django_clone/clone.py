# -*- coding: utf-8 -*-

# Django Clone - https://github.com/mohammadroghani/django-clone
# Copyright © 2016 Mohammad Roghani <mohammadroghani43@gmail.com>
# Copyright © 2016 Amir Keivan Mohtashami <akmohtashami97@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from copy import copy

from django.core.exceptions import ValidationError
from django.db import models
from django.apps import apps


class Cloner(object):

    def __init__(self, *args, **kwargs):

        self.ignored_models = []
        self.blocking_models = []
        self.ignored_fields = []
        self.ignored_instances = {}
        self.blocking_instances = []

        self.apply_limits(*args, **kwargs)

    def apply_limits(self,
                     ignored_models=None,
                     ignored_instances=None,
                     blocking_models=None,
                     ignored_fields=None,
                     blocking_instances=None):

        if ignored_models:
            self.ignored_models.extend([apps.get_model(s) for s in ignored_models])
        if blocking_models:
            self.blocking_models.extend([apps.get_model(s) for s in blocking_models])
        if ignored_fields:
            self.ignored_fields.extend([(apps.get_model(a), b) for a, b in ignored_fields])
        if ignored_instances:
            self.ignored_instances.update(ignored_instances)
        if blocking_instances:
            self.blocking_instances.extend(blocking_instances)

        return self


    def get_all_neighbor_objects(self, obj):
        """
        find all objects that are adjacent to specific object
        """
        return_list = []
        for field in obj._meta.get_fields():
            if field.is_relation:
                if field.many_to_one or field.one_to_one:
                    field_name = field.name
                else:
                    field_name = field.name
                    if field.auto_created:
                        if field.related_name is not None:
                            field_name = field.related_name
                        else:
                            field_name += "_set"

                # Check whether this field should be ignored.
                # We deliberately check the exact type
                # to provide more control when using inheritance.

                blocked = False

                for model, blocked_field_name in self.ignored_fields:
                    if type(obj) == model and field_name == blocked_field_name:
                        blocked = True
                        break
                if blocked:
                    continue

                if field.many_to_one or field.one_to_one:
                    fld = getattr(obj, field_name, None)
                    if fld is not None:
                        return_list.append(fld)
                else:
                    for fld in getattr(obj, field_name).all():
                        return_list.append(fld)
        return return_list

    def get_all_related_object(self, obj):
        """
        find all object that are related to one object
        """
        def _get_all_related_object_recursively(obj, mark):
            """
            recursively go to adjacent objects of an object and find related objects
            it works like dfs
            """
            succeded_in_going_down = True
            while succeded_in_going_down:
                succeded_in_going_down = False
                for field in obj._meta.get_fields():
                    if field.is_relation and field.one_to_one and getattr(field, "parent_link", False):
                        try:
                            obj = getattr(obj, field.name)
                            succeded_in_going_down = True
                            break
                        except:
                            pass
            if (obj.__class__, obj.pk) in mark:
                return []
            mark.update([(obj.__class__, obj.pk)])
            return_list = [obj]
            neighbors = self.get_all_neighbor_objects(obj)
            for fld in neighbors:
                blocked = False
                for model in self.blocking_models:
                    if type(fld) == model:
                        blocked = True
                        break
                if fld in self.blocking_instances:
                    blocked = True
                if blocked:
                    return_list.append(fld)
                elif isinstance(fld, models.Model) and (fld.__class__, fld.pk) not in mark:
                    return_list.extend(_get_all_related_object_recursively(fld, mark))
            return return_list
        mark = set([])
        return _get_all_related_object_recursively(obj, mark)

    def clone(self, obj, editor=None):
        """
        make copy of every objects that are related to one object
        """

        old_to_new_objects_map = self.ignored_instances.copy()
        new_to_old_objects_map = {b: a for a, b in old_to_new_objects_map.items()}

        old_objects = self.get_all_related_object(obj)

        save_queue = []
        for old_object in old_objects:

            ignored = False
            match = None

            if old_object in self.ignored_instances:
                ignored = True
                match = self.ignored_instances[old_object]
            else:
                for model in self.ignored_models:
                    if type(old_object) == model:
                        ignored = True
                        match = old_object
                        break

            if not ignored:
                new_object = copy(old_object)
                new_object.pk = None
                if editor is not None and callable(editor):
                    new_object = editor(new_object)
                save_queue.append((new_object, old_object, -1))
            else:
                old_to_new_objects_map[old_object] = match


        new_objects = []

        while len(save_queue) > 0:

            new_object, old_object, last_time_length = save_queue.pop(0)
            if last_time_length == len(new_objects):
                raise ValueError("Unable to clone due to unique and not-null fields. "
                                 "Use an editor to modify unique values before saving")

            # Updating the relations that their match has already been saved

            try:
                self._update_relations(new_object, old_object, old_to_new_objects_map, lazy=True)
                # Don't use full clean here because
                # it might have not been used on old object
                new_object.validate_unique()
            except ValidationError as e:
                save_queue.append((new_object, old_object, len(new_objects)))
                continue

            new_object_dict = {}
            for field in new_object._meta.get_fields():
                if field.auto_created:
                    continue
                if field.is_relation:
                    parent_link = field.one_to_one and getattr(field.remote_field, "parent_link", False)
                    if parent_link or field.many_to_many or field.one_to_many:
                        continue
                new_object_dict[field.name] = getattr(new_object, field.name, None)

            new_object = new_object.__class__.objects.create(**new_object_dict)
            new_objects.append(new_object)
            old_to_new_objects_map[old_object] = new_object
            new_to_old_objects_map[new_object] = old_object

        # All objects have been saved now. So we have to update
        # all relations that weren't updated previously.
        for new_object in new_objects:
            self._update_relations(new_object, new_to_old_objects_map[new_object], old_to_new_objects_map)
            new_object.save()

        # Many-to-many relations
        for new_object in new_objects:
            for field in new_object._meta.get_fields():
                if field.is_relation and field.many_to_many and field.auto_created is False:
                    for fld in getattr(new_to_old_objects_map[new_object], field.name).all():
                        mapped_fld = old_to_new_objects_map.get(fld, fld)
                        current_field = getattr(new_object, field.name)
                        if mapped_fld not in current_field.all():
                            current_field.add(mapped_fld)
            new_object.save()
        return old_to_new_objects_map[obj]

    def _update_relations(self, new_object, old_object, old_to_new_objects_map, lazy=False):
        for field in new_object._meta.get_fields():
            if field.is_relation and not field.auto_created and (field.many_to_one or field.one_to_one):
                parent_link = field.one_to_one and getattr(field.remote_field, "parent_link", False)
                if parent_link:
                    continue
                field_value = getattr(old_object, field.name, None)

                mapped_value = old_to_new_objects_map.get(field_value, field_value)
                if lazy:
                    try:
                        setattr(new_object, field.name, None)
                    except ValueError:
                        setattr(new_object, field.name, mapped_value)
                else:
                    setattr(new_object, field.name, mapped_value)
