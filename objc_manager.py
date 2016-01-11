import re
from skr_logger import skr_log_warning
import string_utils


_OBJC_BR = '\n\n'
_OBJC_SPACE = '  '


class ObjcManager:

    def __init__(self, manager_name):
        self.manager_name = manager_name
        self.save_commands = []
        self.delete_commands = []
        self.fetch_commands = []

        self.object_name = ''
        self.plural_object_name = ''

        self.objc_variable_list = []

    def set_object_name(self, class_name, plural_class_name):
        self.object_name = class_name
        self.plural_object_name = plural_class_name

    def set_objc_variable_list(self, objc_variable_list):
        self.objc_variable_list = objc_variable_list

    def add_save_command(self, save_command):
        self.save_commands.append(save_command)

    def add_fetch_command(self, fetch_command):
        self.fetch_commands.append(fetch_command)

    def add_delete_command(self, delete_command):
        self.delete_commands.append(delete_command)

    def class_name(self):
        return self.manager_name

    def generate_fetch_declarations(self):
        declaration = ''
        for fetch_command in self.fetch_commands:
            by_list = []
            if fetch_command.where != '':
                by_list = re.split(',', fetch_command.where)

            if not fetch_command.is_plural:
                if len(by_list) == 0:
                    skr_log_warning('Singular often comes with at least one by parameter')
                declaration += '- (nullable LCC{0} *)fetch{0}FromCache{1};\n\n'\
                    .format(self.object_name, self.__convert_bys_to_string(by_list))
            else:
                declaration += '- (NSArray<LCC{0} *> *)fetch{1}FromCache{2};\n\n'\
                    .format(self.object_name, self.plural_object_name, self.__convert_bys_to_string(by_list))
        return declaration

    def generate_fetch_implementations(self):
        impl = ''
        for fetch_command in self.fetch_commands:
            impl += self.__fetch_implementation(fetch_command)
            impl += _OBJC_BR
        return impl

    def generate_constructor_implementation(self):
        impl = '- (instancetype)init {\n'
        impl += string_utils.indent(2)
        impl += 'if (self = [super init]) {\n'
        impl += string_utils.indent(4)
        impl += '_coreManagerHandler = lesschat::{0}Manager::DefaultManager();\n'.format(self.object_name)
        impl += string_utils.indent(2)
        impl += '}\n'
        impl += string_utils.indent(2)
        impl += 'return self;\n'
        impl += '}'
        return impl

    def generate_default_manager_implementation(self):
        impl = '+ (instancetype)defaultManager {\n'
        impl += _OBJC_SPACE
        impl += 'return [LCCDirector defaultDirector].{0}Manager;\n'.format(string_utils.first_char_to_lower(self.object_name))
        impl += '}'
        return impl

    # returns "ById:(NSString *)id name:(NSString *)name" or ""
    def __convert_bys_to_string(self, by_string_list):
        if len(by_string_list) == 0:  # empty string
            return ''
        else:  # "(const std::string& id, const std::string& username)"
            bys_string = 'By'
            it = 0
            for by_string in by_string_list:
                objc_var = self.__objc_var_by_name(by_string)
                if objc_var is not None:
                    if it == 0:
                        bys_string += string_utils.first_char_to_upper(objc_var.parameter()) + ' '
                    else:
                        bys_string += objc_var.parameter() + ' '
                    it += 1
                else:
                    print 'Unknown "{0}" in "by"'.format(by_string)
                    return ''
            bys_string = bys_string[:-1]
            return bys_string

    # returns None if not found
    def __objc_var_by_name(self, name_string):
        for objc_var in self.objc_variable_list:
            if objc_var.name == name_string:
                return objc_var
        return None

    def __fetch_implementation(self, fetch_command):
        by_list = []
        if fetch_command.where != '':
            by_list = re.split(',', fetch_command.where)

        if not fetch_command.is_plural:
            impl = '- (nullable LCC{0} *)fetch{0}FromCache{1} {{\n'\
                    .format(self.object_name, self.__convert_bys_to_string(by_list))
            impl += string_utils.indent(2)
            impl += 'std::unique_ptr<lesschat::{0}> core{0} = _coreManagerHandler->{1};\n'.format(self.object_name, self.__cpp_fetch_method_name(fetch_command))
            impl += string_utils.indent(2)
            impl += 'if (core{0}) {{\n'.format(self.object_name)
            impl += string_utils.indent(4)
            impl += 'return [LCC{0} {1}WithCore{0}:*core{0}];\n'.format(self.object_name, string_utils.first_char_to_lower(self.object_name))
            impl += string_utils.indent(2)
            impl += '}\n'
            impl += string_utils.indent(2)
            impl += 'return nil;\n'
            impl += '}'
            return impl
        else:
            impl = '- (NSArray<LCC{0} *> *)fetch{1}FromCache{2} {{\n'\
                    .format(self.object_name, self.plural_object_name, self.__convert_bys_to_string(by_list))
            impl += string_utils.indent(2)
            impl += 'NSMutableArray *{0} = [NSMutableArray array];\n'.format(string_utils.first_char_to_lower(self.plural_object_name))
            impl += string_utils.indent(2)
            impl += 'std::vector<std::unique_ptr<lesschat::{0}>> core{1} = _coreManagerHandler->{2};\n'.format(self.object_name, self.plural_object_name, self.__cpp_fetch_method_name(fetch_command))
            impl += string_utils.indent(2)
            impl += 'for (auto it = core{0}.begin(); it != core{0}.end(); ++it) {{\n'.format(self.plural_object_name)
            impl += string_utils.indent(4)
            impl += '[{0} addObject:[LCC{1} {2}WithCore{1}:(**it)]];\n'.format(string_utils.first_char_to_lower(self.plural_object_name), self.object_name, string_utils.first_char_to_lower(self.object_name))
            impl += string_utils.indent(2)
            impl += '}\n'
            impl += string_utils.indent(2)
            impl += 'return [{0} copy];\n'.format(string_utils.first_char_to_lower(self.plural_object_name))
            impl += '}\n'
            return impl

    def __cpp_fetch_method_name(self, fetch_command):
        by_list = []
        if fetch_command.where != '':
            by_list = re.split(',', fetch_command.where)

        if not fetch_command.is_plural:
            if len(by_list) == 0:
                skr_log_warning('Singular often comes with at least one by parameter')
            return 'Fetch{0}FromCache{1}'\
                .format(self.object_name, self.__convert_bys_to_cpp_string(by_list))
        else:
            return 'Fetch{0}FromCache{1}'\
                .format(self.plural_object_name, self.__convert_bys_to_cpp_string(by_list))

    # returns "ById([id UTF8String])" or "([id UTF8String], [username UTF8String])" or "()"
    def __convert_bys_to_cpp_string(self, by_string_list):
        if len(by_string_list) == 0:  # ()
            return '()'
        elif len(by_string_list) == 1:  # "ById(const std::string& id)"
            by_string = by_string_list[0]
            objc_var = self.__objc_var_by_name(by_string)
            if objc_var is not None:
                return 'By{0}({1})'.format(objc_var.to_title_style_name(), objc_var.cast_to_cpp_parameter())
            else:
                print 'Unknown "{0}" in "by"'.format(by_string)
                return ''
        else:  # "([id UTF8String], [username UTF8String])"
            bys_string = '('
            for by_string in by_string_list:
                objc_var = self.__objc_var_by_name(by_string)
                if objc_var is not None:
                    bys_string += objc_var.cast_to_cpp_parameter() + ', '
                else:
                    print 'Unknown "{0}" in "by"'.format(by_string)
                    return ''
            bys_string = bys_string[:-2]  # remove last 2 chars
            bys_string += ')'
            return bys_string