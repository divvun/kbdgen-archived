const yaml = require("js-yaml")
const fs = require("fs")
const path = require("path")
const mkdirp = require("mkdirp").sync

const VALID_PROJECT_KEYS = [
  "locales",
  "author",
  "copyright",
  "email",
  "organisation"
]

async function main() {
  if (process.argv.length <= 3) {
    console.log("Usage: convertor <projectYaml> <outputKbdgen>")
    return
  }
  return start(process.argv[2], process.argv[3])
}

function deriveTarget(target) {
  const { supportedTargets, modes, targets, styles } = target

  if (supportedTargets != null) {
    if (supportedTargets.includes("osx") && supportedTargets.includes("win")) {
      // It's just normal desktop
      return "desktop"
    } else if (supportedTargets.includes("osx")) {
      return "mac"
    } else if (supportedTargets.includes("win")) {
      return "win"
    } else if (supportedTargets.includes("android") || supportedTargets.includes("ios")) {
      return "mobile"
    }

    // Fall through to other heuristics if not return
  }

  if (styles != null || Object.keys(modes).find((v) => v.startsWith("mobile-")) != null) {
    return "mobile"
  }

  if (Object.keys(modes).find((v) => v.startsWith("osx-")) != null) {
    return "mac"
  }

  if (targets.win != null) {
    return "win"
  }

  return "desktop"
}

function injectModesAndDeadkeys(newModes, newDeadkeys, guessedTarget, layout) {
  const { modes } = layout
  const deadKeys = layout.deadKeys || {}

  for (const modeKey in modes) {
    const modeValue = modes[modeKey]
    const deadkeysValue = deadKeys[modeKey]

    const [prefix, suffix] = modeKey.split("-")

    if (prefix === "mobile") {
      if (newModes.mobile == null) {
        newModes.mobile = {}
      }
      newModes.mobile[suffix] = modeValue
    } else if (prefix == "osx") {
      if (newModes.mac == null) {
        newModes.mac = {}
      }

      newModes.mac[suffix] = modeValue

      if (deadkeysValue != null) {
        if (newDeadkeys.mac == null) {
          newDeadkeys.mac = {}
        }

        newDeadkeys.mac[suffix] = deadkeysValue
      }
    } else {
      // Do some heuristics
      if (newModes[guessedTarget] == null) {
        newModes[guessedTarget] = {}
      }

      newModes[guessedTarget][suffix] = modeValue

      if (deadkeysValue != null) {
        if (newDeadkeys[guessedTarget] == null) {
          newDeadkeys[guessedTarget] = {}
        }

        newDeadkeys[guessedTarget][suffix] = deadkeysValue
      }
    }
  }
}

function injectLongPresses(newLongpress, layout) {
  const { longpress } = layout

  if (longpress == null) {
    return
  }

  Object.assign(newLongpress, longpress)
}

function cleanModeKeys(obj) {
  const o = {}
  for (const key in obj) {
    const [prefix, suffix] = key.split("-")
    o[suffix] = obj[key]
  }
  return o
}

function cleanLocales(obj) {
  const o = {}
  for (const key in obj) {
    const newKey = key.replace(/_/g, "-")
    o[newKey] = obj[key]
  }
  return o
}

function recurseTransforms(acc, transforms) {
  for (const key in transforms) {
    const value = transforms[key]

    if (typeof value !== "string") {
      if (typeof acc[key] === "string") {
        throw new TypeError(`Invalid transform key: ${key}`)
      }
      
      if (acc[key] == null) {
        acc[key] = {}
      }

      recurseTransforms(acc[key], value)
    } else {
      acc[key] = value
    }
  }
}

function injectTransforms(newTransforms, layout) {
  const { transforms } = layout

  if (transforms == null) {
    return
  }

  recurseTransforms(newTransforms, transforms)
}

function injectLayoutTargets(newTargets, targets) {
  for (let k in targets) {
    if (k === "osx") {
      k = "mac"
    }

    if (newTargets[k] == null) {
      newTargets[k] = {}
    }

    Object.assign(newTargets[k], targets[k])
  }
}

function injectLegacyName(newTargets, guessedTarget, layout) {
  if (guessedTarget === "mobile") {
    if (newTargets.ios == null) {
      newTargets.ios = {}
    }
    if (newTargets.android == null) {
      newTargets.android = {}
    }

    newTargets.android.legacyName = layout.internalName
    newTargets.ios.legacyName = layout.internalName
  }

  if (guessedTarget === "win") {
    if (newTargets.win == null) {
      newTargets.win = {}
    }

    newTargets.win.legacyName = layout.internalName
  }
}

function injectProjectTarget(target, key, oldProjectPath, bundlePath) {
  const resourcesPath = path.join(bundlePath, "resources", key)
  mkdirp(resourcesPath)

  if (key === "mac") {
    if (target.resources == null) {
      return
    }

    oldResourcesPath = path.resolve(oldProjectPath, target.resources)

    delete target.resources

    const prefixes = [
      "background",
      "license",
      "welcome",
      "readme",
      "conclusion"
    ]

    for (const prefix of prefixes) {
      let thing = null

      if (target[prefix] == null) {
        // Need to derive the file name from the resources dir
        const f = fs.readdirSync(oldResourcesPath).find((f) => f.startsWith(`${prefix}.`))
        if (f != null) {
          thing = path.join(oldResourcesPath, f)
        }

      } else {
        thing = path.resolve(oldResourcesPath, target[prefix])
        delete target[prefix]
      }

      if (thing == null || !fs.existsSync(thing)) {
        continue
      }

      const ext = path.extname(thing)

      fs.copyFileSync(thing, path.join(resourcesPath, `${prefix}${ext}`))
    }

    // resources?: string;
    // background?: string;
    // license?: string;
    // welcome?: string;
    // readme?: string;
    // conclusion?: string;


  } else if (key === "win") {

  }
}

async function start(projectYamlPath, bundlePath) {
  const layoutsPath = path.join(bundlePath, "layouts")
  const targetsPath = path.join(bundlePath, "targets")
  const resourcesPath = path.join(bundlePath, "resources")

  // Create new bundle directory first + subdirs
  mkdirp(bundlePath)
  mkdirp(layoutsPath)
  mkdirp(targetsPath)
  mkdirp(resourcesPath)

  const oldProject = yaml.safeLoad(fs.readFileSync(projectYamlPath, "utf8"))
  const newProject = {}
  
  for (const k of VALID_PROJECT_KEYS) {
    if (oldProject[k] != null) {
      newProject[k] = oldProject[k]
    }
  }

  newProject.locales = cleanLocales(newProject.locales)

  // Create basic new project
  fs.writeFileSync(path.join(bundlePath, "project.yaml"), yaml.safeDump(newProject), "utf8")

  // Create new target files
  const targets = oldProject.targets || {}
  for (let key in targets) {
    const target = targets[key]

    if (key === "osx") {
      key = "mac"
    }

    injectProjectTarget(target, key, path.resolve(projectYamlPath, ".."), bundlePath)

    fs.writeFileSync(path.join(targetsPath, `${key}.yaml`), yaml.safeDump(target), "utf8")
  }

  // Handle new layouts
  const layoutsByLocale = {}

  for (const layoutKey of oldProject.layouts) {
    const layout = yaml.safeLoad(fs.readFileSync(path.resolve(projectYamlPath, "..", `${layoutKey}.yaml`), "utf8"))
    if (layoutsByLocale[layout.locale] == null) {
      layoutsByLocale[layout.locale] = []
    }

    layoutsByLocale[layout.locale].push(layout)
  }
  
  for (const locale in layoutsByLocale) {
    const layouts = layoutsByLocale[locale]

    const newLayout = {
      displayNames: cleanLocales(layouts[0].displayNames)
    }

    const decimalLayout = layouts.find(x => x.decimal)
    if (decimalLayout != null) {
      newLayout.decimal = decimalLayout.decimal
    }

    let out = yaml.safeDump(newLayout, { lineWidth: 240 })

    const newLayout2 = {}
    const newLayout3 = {}

    const newModes = {}
    newLayout2.modes = newModes

    const newDeadkeys = {}
    newLayout3.deadKeys = newDeadkeys

    const newTransforms = {}
    newLayout2.transforms = newTransforms
    
    const newLongpress = {}
    newLayout2.longpress = newLongpress

    const newTargets = {}
    newLayout3.targets = newTargets

    for (const layout of layouts) {
      const guessedTarget = deriveTarget(layout)

      injectModesAndDeadkeys(newModes, newDeadkeys, guessedTarget, layout)
      injectTransforms(newTransforms, layout)
      injectLongPresses(newLongpress, layout)

      if (layout.special && layout.special.space) {
        if (newLayout.space == null) {
          newLayout.space = {}
        }

        newLayout.space[guessedTarget] = cleanModeKeys(layout.special.space)
      }

      if (layout.targets) {
        injectLayoutTargets(newTargets, layout.targets)
      }
      injectLegacyName(newTargets, guessedTarget, layout)

      if (layout.strings != null) {
        newLayout.strings = layout.strings
      }
    }
    
    if (Object.keys(newDeadkeys).length == 0) {
      delete newLayout3.deadKeys
    }
    if (Object.keys(newLongpress).length == 0) {
      delete newLayout2.longpress
    }
    if (Object.keys(newTargets).length == 0) {
      delete newLayout3.targets
    }
    if (Object.keys(newTransforms).length == 0) {
      delete newLayout2.transforms
    }

    out += yaml.safeDump(newLayout2, { lineWidth: 240 })
    out += yaml.safeDump(newLayout3, { lineWidth: 240, flowLevel: 3 })
    
    fs.writeFileSync(path.join(layoutsPath, `${locale.replace(/_/g, "-")}.yaml`), out, "utf8")
  }
}

main().then(() => process.exit(1)).catch((error) => {
  console.error(error.stack)
  process.exit(1)
})