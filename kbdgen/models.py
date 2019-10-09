class ProjectDesc:
  def __init__(self, name, description):
    self.name = name
    self.description = description

  def get_name(self):
    return self.name

  def get_description(self):
    return self.description

  @staticmethod
  def decode(data):
    f_name = data["name"]

    if not isinstance(f_name, str):
      raise Exception("not a string")

    f_description = data["description"]

    if not isinstance(f_description, str):
      raise Exception("not a string")

    return ProjectDesc(f_name, f_description)

  def encode(self):
    data = dict()

    if self.name is None:
      raise Exception("name: is a required field")

    data["name"] = self.name

    if self.description is None:
      raise Exception("description: is a required field")

    data["description"] = self.description

    return data

  def __repr__(self):
    return "<ProjectDesc name:{!r}, description:{!r}>".format(self.name, self.description)

class Project:
  def __init__(self, locales, author, email, copyright, organisation):
    self.locales = locales
    self.author = author
    self.email = email
    self.copyright = copyright
    self.organisation = organisation

  def get_locales(self):
    return self.locales

  def get_author(self):
    return self.author

  def get_email(self):
    return self.email

  def get_copyright(self):
    return self.copyright

  def get_organisation(self):
    return self.organisation

  @staticmethod
  def decode(data):
    f_locales = data["locales"]

    if not isinstance(f_locales, dict):
      raise Exception("not an object")

    _o0 = {}

    for _k0, _v0 in f_locales.items():
      if not isinstance(_k0, str):
        raise Exception("not a string")
      _v0 = ProjectDesc.decode(_v0)
      _o0[_k0] = _v0

    f_locales = _o0

    f_author = data["author"]

    if not isinstance(f_author, str):
      raise Exception("not a string")

    f_email = data["email"]

    if not isinstance(f_email, str):
      raise Exception("not a string")

    f_copyright = data["copyright"]

    if not isinstance(f_copyright, str):
      raise Exception("not a string")

    f_organisation = data["organisation"]

    if not isinstance(f_organisation, str):
      raise Exception("not a string")

    return Project(f_locales, f_author, f_email, f_copyright, f_organisation)

  def encode(self):
    data = dict()

    if self.locales is None:
      raise Exception("locales: is a required field")

    data["locales"] = dict((k, v.encode()) for (k, v) in self.locales.items())

    if self.author is None:
      raise Exception("author: is a required field")

    data["author"] = self.author

    if self.email is None:
      raise Exception("email: is a required field")

    data["email"] = self.email

    if self.copyright is None:
      raise Exception("copyright: is a required field")

    data["copyright"] = self.copyright

    if self.organisation is None:
      raise Exception("organisation: is a required field")

    data["organisation"] = self.organisation

    return data

  def __repr__(self):
    return "<Project locales:{!r}, author:{!r}, email:{!r}, copyright:{!r}, organisation:{!r}>".format(self.locales, self.author, self.email, self.copyright, self.organisation)

class LayoutStrings:
  def __init__(self, space, _return):
    self.space = space
    self._return = _return

  def get_space(self):
    return self.space

  def get_return(self):
    return self._return

  @staticmethod
  def decode(data):
    f_space = data["space"]

    if not isinstance(f_space, str):
      raise Exception("not a string")

    f__return = data["return"]

    if not isinstance(f__return, str):
      raise Exception("not a string")

    return LayoutStrings(f_space, f__return)

  def encode(self):
    data = dict()

    if self.space is None:
      raise Exception("space: is a required field")

    data["space"] = self.space

    if self._return is None:
      raise Exception("return: is a required field")

    data["return"] = self._return

    return data

  def __repr__(self):
    return "<LayoutStrings space:{!r}, return:{!r}>".format(self.space, self._return)

class DeriveOptions:
  def __init__(self, transforms):
    self.transforms = transforms

  def get_transforms(self):
    return self.transforms

  @staticmethod
  def decode(data):
    f_transforms = None

    if "transforms" in data:
      f_transforms = data["transforms"]

      if f_transforms is not None:
        if not isinstance(f_transforms, bool):
          raise Exception("not a boolean")

    return DeriveOptions(f_transforms)

  def encode(self):
    data = dict()

    if self.transforms is not None:
      data["transforms"] = self.transforms

    return data

  def __repr__(self):
    return "<DeriveOptions transforms:{!r}>".format(self.transforms)

class Layout:
  def __init__(self, display_names, modes, decimal, space, dead_keys, longpress, transforms, strings, derive, targets):
    self.display_names = display_names
    self.modes = modes
    self.decimal = decimal
    self.space = space
    self.dead_keys = dead_keys
    self.longpress = longpress
    self.transforms = transforms
    self.strings = strings
    self.derive = derive
    self.targets = targets

  def get_display_names(self):
    """
    The display names for the layout, keyed by locale.
    """
    return self.display_names

  def get_modes(self):
    """
    The different modes.
    """
    return self.modes

  def get_decimal(self):
    """
    The decimal key. Nominally a '.' or ','.
    """
    return self.decimal

  def get_space(self):
    """
    An override for space keys on some OSes. Keyed by target.
    """
    return self.space

  def get_dead_keys(self):
    """
    Dead keys present, keyed by layer code.
    """
    return self.dead_keys

  def get_longpress(self):
    """
    The items to be shown when a key is long-pressed. Values are space separated in one string.
    """
    return self.longpress

  def get_transforms(self):
    """
    The chain of inputs necessary to provide an output after a deadkey is pressed. Keyed by each individual input.
    """
    return self.transforms

  def get_strings(self):
    """
    Strings to be shown on some OSes
    """
    return self.strings

  def get_derive(self):
    """
    Derives
    """
    return self.derive

  def get_targets(self):
    """
    Targets...
    """
    return self.targets

  @staticmethod
  def decode(data):
    f_display_names = data["displayNames"]

    if not isinstance(f_display_names, dict):
      raise Exception("not an object")

    _o0 = {}

    for _k0, _v0 in f_display_names.items():
      if not isinstance(_k0, str):
        raise Exception("not a string")
      if not isinstance(_v0, str):
        raise Exception("not a string")
      _o0[_k0] = _v0

    f_display_names = _o0

    f_modes = data["modes"]

    if not isinstance(f_modes, dict):
      raise Exception("not an object")

    _o0 = {}

    for _k0, _v0 in f_modes.items():
      if not isinstance(_k0, str):
        raise Exception("not a string")
      _o0[_k0] = _v0

    f_modes = _o0

    f_decimal = None

    if "decimal" in data:
      f_decimal = data["decimal"]

      if f_decimal is not None:
        if not isinstance(f_decimal, str):
          raise Exception("not a string")

    f_space = None

    if "space" in data:
      f_space = data["space"]

      if f_space is not None:
        if not isinstance(f_space, dict):
          raise Exception("not an object")

        _o0 = {}

        for _k0, _v0 in f_space.items():
          if not isinstance(_k0, str):
            raise Exception("not a string")
          _o0[_k0] = _v0

        f_space = _o0

    f_dead_keys = None

    if "deadKeys" in data:
      f_dead_keys = data["deadKeys"]

      if f_dead_keys is not None:
        if not isinstance(f_dead_keys, dict):
          raise Exception("not an object")

        _o0 = {}

        for _k0, _v0 in f_dead_keys.items():
          if not isinstance(_k0, str):
            raise Exception("not a string")
          _o0[_k0] = _v0

        f_dead_keys = _o0

    f_longpress = None

    if "longpress" in data:
      f_longpress = data["longpress"]

      if f_longpress is not None:
        if not isinstance(f_longpress, dict):
          raise Exception("not an object")

        _o0 = {}

        for _k0, _v0 in f_longpress.items():
          if not isinstance(_k0, str):
            raise Exception("not a string")
          if not isinstance(_v0, str):
            raise Exception("not a string")
          _o0[_k0] = _v0

        f_longpress = _o0

    f_transforms = None

    if "transforms" in data:
      f_transforms = data["transforms"]

      if f_transforms is not None:
        if not isinstance(f_transforms, dict):
          raise Exception("not an object")

        _o0 = {}

        for _k0, _v0 in f_transforms.items():
          if not isinstance(_k0, str):
            raise Exception("not a string")
          _o0[_k0] = _v0

        f_transforms = _o0

    f_strings = None

    if "strings" in data:
      f_strings = data["strings"]

      if f_strings is not None:
        f_strings = LayoutStrings.decode(f_strings)

    f_derive = None

    if "derive" in data:
      f_derive = data["derive"]

      if f_derive is not None:
        f_derive = DeriveOptions.decode(f_derive)

    f_targets = None

    if "targets" in data:
      f_targets = data["targets"]

      if f_targets is not None:
        if not isinstance(f_targets, dict):
          raise Exception("not an object")

        _o0 = {}

        for _k0, _v0 in f_targets.items():
          if not isinstance(_k0, str):
            raise Exception("not a string")
          _o0[_k0] = _v0

        f_targets = _o0

    return Layout(f_display_names, f_modes, f_decimal, f_space, f_dead_keys, f_longpress, f_transforms, f_strings, f_derive, f_targets)

  def encode(self):
    data = dict()

    if self.display_names is None:
      raise Exception("displayNames: is a required field")

    data["displayNames"] = self.display_names

    if self.modes is None:
      raise Exception("modes: is a required field")

    data["modes"] = self.modes

    if self.decimal is not None:
      data["decimal"] = self.decimal

    if self.space is not None:
      data["space"] = self.space

    if self.dead_keys is not None:
      data["deadKeys"] = self.dead_keys

    if self.longpress is not None:
      data["longpress"] = self.longpress

    if self.transforms is not None:
      data["transforms"] = self.transforms

    if self.strings is not None:
      data["strings"] = self.strings.encode()

    if self.derive is not None:
      data["derive"] = self.derive.encode()

    if self.targets is not None:
      data["targets"] = self.targets

    return data

  def __repr__(self):
    return "<Layout display_names:{!r}, modes:{!r}, decimal:{!r}, space:{!r}, dead_keys:{!r}, longpress:{!r}, transforms:{!r}, strings:{!r}, derive:{!r}, targets:{!r}>".format(self.display_names, self.modes, self.decimal, self.space, self.dead_keys, self.longpress, self.transforms, self.strings, self.derive, self.targets)

class LayoutTargetWindows:
  def __init__(self, locale, language_name):
    self.locale = locale
    self.language_name = language_name

  def get_locale(self):
    """
    The actual locale within Windows, as per their broken ISO 639-3 scheme or secret hardcoded lists.
    """
    return self.locale

  def get_language_name(self):
    """
    The language name to be cached, in order to try to mask the ugly ISO code name that often shows.
    """
    return self.language_name

  @staticmethod
  def decode(data):
    f_locale = data["locale"]

    if not isinstance(f_locale, str):
      raise Exception("not a string")

    f_language_name = data["languageName"]

    if not isinstance(f_language_name, str):
      raise Exception("not a string")

    return LayoutTargetWindows(f_locale, f_language_name)

  def encode(self):
    data = dict()

    if self.locale is None:
      raise Exception("locale: is a required field")

    data["locale"] = self.locale

    if self.language_name is None:
      raise Exception("languageName: is a required field")

    data["languageName"] = self.language_name

    return data

  def __repr__(self):
    return "<LayoutTargetWindows locale:{!r}, language_name:{!r}>".format(self.locale, self.language_name)

class LayoutTargetAndroid:
  def __init__(self, minimum_sdk, style):
    self.minimum_sdk = minimum_sdk
    self.style = style

  def get_minimum_sdk(self):
    """
    Minimum SDK can be specified for a specific layout
    """
    return self.minimum_sdk

  def get_style(self):
    """
    Styles
    """
    return self.style

  @staticmethod
  def decode(data):
    f_minimum_sdk = None

    if "minimumSdk" in data:
      f_minimum_sdk = data["minimumSdk"]

      if f_minimum_sdk is not None:
        if not isinstance(f_minimum_sdk, int):
          raise Exception("not an integer")

    f_style = None

    if "style" in data:
      f_style = data["style"]

      if f_style is not None:
        if not isinstance(f_style, dict):
          raise Exception("not an object")

        _o0 = {}

        for _k0, _v0 in f_style.items():
          if not isinstance(_k0, str):
            raise Exception("not a string")
          _o0[_k0] = _v0

        f_style = _o0

    return LayoutTargetAndroid(f_minimum_sdk, f_style)

  def encode(self):
    data = dict()

    if self.minimum_sdk is not None:
      data["minimumSdk"] = self.minimum_sdk

    if self.style is not None:
      data["style"] = self.style

    return data

  def __repr__(self):
    return "<LayoutTargetAndroid minimum_sdk:{!r}, style:{!r}>".format(self.minimum_sdk, self.style)

class TargetAndroid:
  def __init__(self, version, build, package_id, icon, sentry_dsn, show_number_hints, minimum_sdk, bhfst, key_store, key_alias):
    self.version = version
    self.build = build
    self.package_id = package_id
    self.icon = icon
    self.sentry_dsn = sentry_dsn
    self.show_number_hints = show_number_hints
    self.minimum_sdk = minimum_sdk
    self.bhfst = bhfst
    self.key_store = key_store
    self.key_alias = key_alias

  def get_version(self):
    return self.version

  def get_build(self):
    return self.build

  def get_package_id(self):
    return self.package_id

  def get_icon(self):
    return self.icon

  def get_sentry_dsn(self):
    return self.sentry_dsn

  def get_show_number_hints(self):
    return self.show_number_hints

  def get_minimum_sdk(self):
    return self.minimum_sdk

  def get_bhfst(self):
    return self.bhfst

  def get_key_store(self):
    return self.key_store

  def get_key_alias(self):
    return self.key_alias

  @staticmethod
  def decode(data):
    f_version = data["version"]

    if not isinstance(f_version, str):
      raise Exception("not a string")

    f_build = data["build"]

    if not isinstance(f_build, int):
      raise Exception("not an integer")

    f_package_id = data["packageId"]

    if not isinstance(f_package_id, str):
      raise Exception("not a string")

    f_icon = None

    if "icon" in data:
      f_icon = data["icon"]

      if f_icon is not None:
        if not isinstance(f_icon, str):
          raise Exception("not a string")

    f_sentry_dsn = None

    if "sentryDsn" in data:
      f_sentry_dsn = data["sentryDsn"]

      if f_sentry_dsn is not None:
        if not isinstance(f_sentry_dsn, str):
          raise Exception("not a string")

    f_show_number_hints = None

    if "showNumberHints" in data:
      f_show_number_hints = data["showNumberHints"]

      if f_show_number_hints is not None:
        if not isinstance(f_show_number_hints, bool):
          raise Exception("not a boolean")

    f_minimum_sdk = None

    if "minimumSdk" in data:
      f_minimum_sdk = data["minimumSdk"]

      if f_minimum_sdk is not None:
        if not isinstance(f_minimum_sdk, int):
          raise Exception("not an integer")

    f_bhfst = None

    if "bhfst" in data:
      f_bhfst = data["bhfst"]

      if f_bhfst is not None:
        if not isinstance(f_bhfst, bool):
          raise Exception("not a boolean")

    f_key_store = None

    if "keyStore" in data:
      f_key_store = data["keyStore"]

      if f_key_store is not None:
        if not isinstance(f_key_store, str):
          raise Exception("not a string")

    f_key_alias = None

    if "keyAlias" in data:
      f_key_alias = data["keyAlias"]

      if f_key_alias is not None:
        if not isinstance(f_key_alias, str):
          raise Exception("not a string")

    return TargetAndroid(f_version, f_build, f_package_id, f_icon, f_sentry_dsn, f_show_number_hints, f_minimum_sdk, f_bhfst, f_key_store, f_key_alias)

  def encode(self):
    data = dict()

    if self.version is None:
      raise Exception("version: is a required field")

    data["version"] = self.version

    if self.build is None:
      raise Exception("build: is a required field")

    data["build"] = self.build

    if self.package_id is None:
      raise Exception("packageId: is a required field")

    data["packageId"] = self.package_id

    if self.icon is not None:
      data["icon"] = self.icon

    if self.sentry_dsn is not None:
      data["sentryDsn"] = self.sentry_dsn

    if self.show_number_hints is not None:
      data["showNumberHints"] = self.show_number_hints

    if self.minimum_sdk is not None:
      data["minimumSdk"] = self.minimum_sdk

    if self.bhfst is not None:
      data["bhfst"] = self.bhfst

    if self.key_store is not None:
      data["keyStore"] = self.key_store

    if self.key_alias is not None:
      data["keyAlias"] = self.key_alias

    return data

  def __repr__(self):
    return "<TargetAndroid version:{!r}, build:{!r}, package_id:{!r}, icon:{!r}, sentry_dsn:{!r}, show_number_hints:{!r}, minimum_sdk:{!r}, bhfst:{!r}, key_store:{!r}, key_alias:{!r}>".format(self.version, self.build, self.package_id, self.icon, self.sentry_dsn, self.show_number_hints, self.minimum_sdk, self.bhfst, self.key_store, self.key_alias)

class TargetIOS:
  def __init__(self, version, build, package_id, icon, bundle_name, team_id, code_sign_id, sentry_dsn, about_dir, bhfst):
    self.version = version
    self.build = build
    self.package_id = package_id
    self.icon = icon
    self.bundle_name = bundle_name
    self.team_id = team_id
    self.code_sign_id = code_sign_id
    self.sentry_dsn = sentry_dsn
    self.about_dir = about_dir
    self.bhfst = bhfst

  def get_version(self):
    return self.version

  def get_build(self):
    return self.build

  def get_package_id(self):
    return self.package_id

  def get_icon(self):
    return self.icon

  def get_bundle_name(self):
    return self.bundle_name

  def get_team_id(self):
    return self.team_id

  def get_code_sign_id(self):
    return self.code_sign_id

  def get_sentry_dsn(self):
    return self.sentry_dsn

  def get_about_dir(self):
    return self.about_dir

  def get_bhfst(self):
    return self.bhfst

  @staticmethod
  def decode(data):
    f_version = data["version"]

    if not isinstance(f_version, str):
      raise Exception("not a string")

    f_build = data["build"]

    if not isinstance(f_build, int):
      raise Exception("not an integer")

    f_package_id = data["packageId"]

    if not isinstance(f_package_id, str):
      raise Exception("not a string")

    f_icon = None

    if "icon" in data:
      f_icon = data["icon"]

      if f_icon is not None:
        if not isinstance(f_icon, str):
          raise Exception("not a string")

    f_bundle_name = data["bundleName"]

    if not isinstance(f_bundle_name, str):
      raise Exception("not a string")

    f_team_id = None

    if "teamId" in data:
      f_team_id = data["teamId"]

      if f_team_id is not None:
        if not isinstance(f_team_id, str):
          raise Exception("not a string")

    f_code_sign_id = None

    if "codeSignId" in data:
      f_code_sign_id = data["codeSignId"]

      if f_code_sign_id is not None:
        if not isinstance(f_code_sign_id, str):
          raise Exception("not a string")

    f_sentry_dsn = None

    if "sentryDsn" in data:
      f_sentry_dsn = data["sentryDsn"]

      if f_sentry_dsn is not None:
        if not isinstance(f_sentry_dsn, str):
          raise Exception("not a string")

    f_about_dir = None

    if "aboutDir" in data:
      f_about_dir = data["aboutDir"]

      if f_about_dir is not None:
        if not isinstance(f_about_dir, str):
          raise Exception("not a string")

    f_bhfst = None

    if "bhfst" in data:
      f_bhfst = data["bhfst"]

      if f_bhfst is not None:
        if not isinstance(f_bhfst, bool):
          raise Exception("not a boolean")

    return TargetIOS(f_version, f_build, f_package_id, f_icon, f_bundle_name, f_team_id, f_code_sign_id, f_sentry_dsn, f_about_dir, f_bhfst)

  def encode(self):
    data = dict()

    if self.version is None:
      raise Exception("version: is a required field")

    data["version"] = self.version

    if self.build is None:
      raise Exception("build: is a required field")

    data["build"] = self.build

    if self.package_id is None:
      raise Exception("packageId: is a required field")

    data["packageId"] = self.package_id

    if self.icon is not None:
      data["icon"] = self.icon

    if self.bundle_name is None:
      raise Exception("bundleName: is a required field")

    data["bundleName"] = self.bundle_name

    if self.team_id is not None:
      data["teamId"] = self.team_id

    if self.code_sign_id is not None:
      data["codeSignId"] = self.code_sign_id

    if self.sentry_dsn is not None:
      data["sentryDsn"] = self.sentry_dsn

    if self.about_dir is not None:
      data["aboutDir"] = self.about_dir

    if self.bhfst is not None:
      data["bhfst"] = self.bhfst

    return data

  def __repr__(self):
    return "<TargetIOS version:{!r}, build:{!r}, package_id:{!r}, icon:{!r}, bundle_name:{!r}, team_id:{!r}, code_sign_id:{!r}, sentry_dsn:{!r}, about_dir:{!r}, bhfst:{!r}>".format(self.version, self.build, self.package_id, self.icon, self.bundle_name, self.team_id, self.code_sign_id, self.sentry_dsn, self.about_dir, self.bhfst)

class TargetWindows:
  def __init__(self, version, app_name, url, uuid, code_sign_pfx, custom_locales, license_path, readme_path):
    self.version = version
    self.app_name = app_name
    self.url = url
    self.uuid = uuid
    self.code_sign_pfx = code_sign_pfx
    self.custom_locales = custom_locales
    self.license_path = license_path
    self.readme_path = readme_path

  def get_version(self):
    return self.version

  def get_app_name(self):
    return self.app_name

  def get_url(self):
    return self.url

  def get_uuid(self):
    return self.uuid

  def get_code_sign_pfx(self):
    return self.code_sign_pfx

  def get_custom_locales(self):
    return self.custom_locales

  def get_license_path(self):
    return self.license_path

  def get_readme_path(self):
    return self.readme_path

  @staticmethod
  def decode(data):
    f_version = data["version"]

    if not isinstance(f_version, str):
      raise Exception("not a string")

    f_app_name = data["appName"]

    if not isinstance(f_app_name, str):
      raise Exception("not a string")

    f_url = data["url"]

    if not isinstance(f_url, str):
      raise Exception("not a string")

    f_uuid = data["uuid"]

    if not isinstance(f_uuid, str):
      raise Exception("not a string")

    f_code_sign_pfx = None

    if "codeSignPfx" in data:
      f_code_sign_pfx = data["codeSignPfx"]

      if f_code_sign_pfx is not None:
        if not isinstance(f_code_sign_pfx, str):
          raise Exception("not a string")

    f_custom_locales = None

    if "customLocales" in data:
      f_custom_locales = data["customLocales"]

      if f_custom_locales is not None:
        if not isinstance(f_custom_locales, str):
          raise Exception("not a string")

    f_license_path = None

    if "licensePath" in data:
      f_license_path = data["licensePath"]

      if f_license_path is not None:
        if not isinstance(f_license_path, str):
          raise Exception("not a string")

    f_readme_path = None

    if "readmePath" in data:
      f_readme_path = data["readmePath"]

      if f_readme_path is not None:
        if not isinstance(f_readme_path, str):
          raise Exception("not a string")

    return TargetWindows(f_version, f_app_name, f_url, f_uuid, f_code_sign_pfx, f_custom_locales, f_license_path, f_readme_path)

  def encode(self):
    data = dict()

    if self.version is None:
      raise Exception("version: is a required field")

    data["version"] = self.version

    if self.app_name is None:
      raise Exception("appName: is a required field")

    data["appName"] = self.app_name

    if self.url is None:
      raise Exception("url: is a required field")

    data["url"] = self.url

    if self.uuid is None:
      raise Exception("uuid: is a required field")

    data["uuid"] = self.uuid

    if self.code_sign_pfx is not None:
      data["codeSignPfx"] = self.code_sign_pfx

    if self.custom_locales is not None:
      data["customLocales"] = self.custom_locales

    if self.license_path is not None:
      data["licensePath"] = self.license_path

    if self.readme_path is not None:
      data["readmePath"] = self.readme_path

    return data

  def __repr__(self):
    return "<TargetWindows version:{!r}, app_name:{!r}, url:{!r}, uuid:{!r}, code_sign_pfx:{!r}, custom_locales:{!r}, license_path:{!r}, readme_path:{!r}>".format(self.version, self.app_name, self.url, self.uuid, self.code_sign_pfx, self.custom_locales, self.license_path, self.readme_path)

class TargetMacOS:
  def __init__(self, version, build, package_id, icon, bundle_name, team_id, code_sign_id):
    self.version = version
    self.build = build
    self.package_id = package_id
    self.icon = icon
    self.bundle_name = bundle_name
    self.team_id = team_id
    self.code_sign_id = code_sign_id

  def get_version(self):
    return self.version

  def get_build(self):
    return self.build

  def get_package_id(self):
    return self.package_id

  def get_icon(self):
    return self.icon

  def get_bundle_name(self):
    return self.bundle_name

  def get_team_id(self):
    return self.team_id

  def get_code_sign_id(self):
    return self.code_sign_id

  @staticmethod
  def decode(data):
    f_version = data["version"]

    if not isinstance(f_version, str):
      raise Exception("not a string")

    f_build = data["build"]

    if not isinstance(f_build, int):
      raise Exception("not an integer")

    f_package_id = data["packageId"]

    if not isinstance(f_package_id, str):
      raise Exception("not a string")

    f_icon = None

    if "icon" in data:
      f_icon = data["icon"]

      if f_icon is not None:
        if not isinstance(f_icon, str):
          raise Exception("not a string")

    f_bundle_name = data["bundleName"]

    if not isinstance(f_bundle_name, str):
      raise Exception("not a string")

    f_team_id = None

    if "teamId" in data:
      f_team_id = data["teamId"]

      if f_team_id is not None:
        if not isinstance(f_team_id, str):
          raise Exception("not a string")

    f_code_sign_id = None

    if "codeSignId" in data:
      f_code_sign_id = data["codeSignId"]

      if f_code_sign_id is not None:
        if not isinstance(f_code_sign_id, str):
          raise Exception("not a string")

    return TargetMacOS(f_version, f_build, f_package_id, f_icon, f_bundle_name, f_team_id, f_code_sign_id)

  def encode(self):
    data = dict()

    if self.version is None:
      raise Exception("version: is a required field")

    data["version"] = self.version

    if self.build is None:
      raise Exception("build: is a required field")

    data["build"] = self.build

    if self.package_id is None:
      raise Exception("packageId: is a required field")

    data["packageId"] = self.package_id

    if self.icon is not None:
      data["icon"] = self.icon

    if self.bundle_name is None:
      raise Exception("bundleName: is a required field")

    data["bundleName"] = self.bundle_name

    if self.team_id is not None:
      data["teamId"] = self.team_id

    if self.code_sign_id is not None:
      data["codeSignId"] = self.code_sign_id

    return data

  def __repr__(self):
    return "<TargetMacOS version:{!r}, build:{!r}, package_id:{!r}, icon:{!r}, bundle_name:{!r}, team_id:{!r}, code_sign_id:{!r}>".format(self.version, self.build, self.package_id, self.icon, self.bundle_name, self.team_id, self.code_sign_id)
