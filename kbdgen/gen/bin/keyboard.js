class Keyboard {
  static install(descriptor) {
    let contextId = -1
    const kbd = new Keyboard(descriptor)

    chrome.input.ime.onFocus.addListener((context) => {
      contextId = context.contextID
    })

    chrome.input.ime.onBlur.addListener((context) => {
      contextId = -1
    })

    chrome.input.ime.onKeyEvent.addListener((keyboardId, keyData) => {
      console.log(keyboardId, JSON.stringify(keyData))
      if (keyData.type === "keydown") {
        const result = kbd.parseInput(keyboardId, keyData)
        console.log(result)
        
        if (result == null) {
          // Pass through the default value
          return false
        }

        chrome.input.ime.commitText({
            contextID: contextId,
            text: result
        })

        return true
      } else if (keyData.type === "keyup") {
        kbd.parseKeyUp(keyData)
        return false
      }
      
      return false
    })
  }

  static test(listener, descriptor, callback) {
    const kbd = new Keyboard(descriptor)

    listener.addEventListener("keydown", (event) => {
      console.log(event)

      const input = {
        capsLock: event.getModifierState("CapsLock"),
        ctrlKey: event.ctrlKey,
        shiftKey: event.shiftKey,
        altKey: event.altKey,
        code: event.code
      }

      console.log(input)
      
      const result = kbd.parseInput(input)

      if (result != null) {
        callback(result)
      }
    })
  }

  constructor(descriptor) {
    this.descriptor = descriptor
    this.transformRef = null
  }

  *deriveFallbackLayers(layer) {
    yield layer

    if (layer === "default") {
      return
    }
  
    const hasCaps = layer.includes("caps")
    const hasShift = layer.includes("shift")

    if (hasCaps && layer !== "caps") {
      yield "caps"
    }

    if (hasShift && layer !== "shift") {
      yield "shift"
    }
  
    yield "default"
  }

  deadKey(keyboardId, value, layer) {
    if (this.transformRef != null) {
      return null
    }
    
    console.log("DeadKey:", value, layer)
    const deadKeyLayer = this.descriptor[keyboardId].deadKeys[layer]

    if (deadKeyLayer == null) {
      console.log("DeadKey: nope")
      return null
    }

    if (deadKeyLayer == null || !deadKeyLayer.includes(value)) {
      // Not a dead key
      console.log("DeadKey: no value")
      return null
    }

    console.log("DeadKey: transforming")
    this.transformRef = this.descriptor[keyboardId].transforms[value]
    return this.transformRef
  }

  transform(value) {
    const ref = this.transformRef

    console.log("transformRef:", ref)

    if (ref == null) {
      return null
    }

    const t = ref[value]
    console.log("t:", t, value)

    // If the current transform is not valid for the list, return nothing
    // This is what other kbds do on Chrome OS.
    if (t == null) {
      return null
    }

    return t
  }

  processInput(keyboardId, code, startingLayerName) {
    console.log(keyboardId, code)

    for (const layerName of this.deriveFallbackLayers(startingLayerName)) {
      console.log(layerName)

      let layer = this.descriptor[keyboardId].layers[layerName]

      console.log(layer)

      if (layer == null) {
        continue
      }

      // Check for first dead key press
      const deadKeyRef = this.deadKey(keyboardId, layer[code], layerName)
      if (deadKeyRef != null) {
        this.transformRef = deadKeyRef
        return null
      }

      let value

      // Space special case
      if (code === "Space") {
        value = this.descriptor[keyboardId].space[startingLayerName] || " "
      }

      // If nothing is valid, run away to next layer fallback
      if (value == null && layer[code] != null) {
        value = layer[code]
      }

      if (value == null) {
        continue
      }

      // If we have a current transform stack, look into it
      if (this.transformRef != null) {
        console.log("Try transform:", this.transformRef)
        
        const t = this.transform(value)

        // If it's a string, we're at the end of the line
        if (typeof t === "string") {
          this.transformRef = null
          return t
        }

        // Otherwise, buckle up for more transforms!
        this.transformRef = t
        return null
      }

      // Otherwise we just return the ordinary value
      return value
    }
  }

  handleAltRightKey(code) {
    if (code === "AltRight") {
      this.isAltGrKeyHeld = true
      return true
    }

    return false
  }

  parseKeyUp({ code, ctrlKey, shiftKey, capsLock }) {
    if (code == "AltRight") {
      this.isAltGrKeyHeld = false
    }
  }

  parseInput(keyboardId, {
    code,
    ctrlKey,
    shiftKey,
    capsLock
  }) {
    let layerName
    const o = []

    if (this.handleAltRightKey(code)) {
      return null
    }
    
    if (capsLock) {
      o.push("caps")
    }

    if (ctrlKey) {
      o.push("ctrl")
    }

    if (this.isAltGrKeyHeld) {
      o.push("alt")
    }

    if (shiftKey) {
      o.push("shift")
    }

    if (o.length > 0) {
      layerName = o.join("+")
    } else {
      layerName = "default"
    }

    return this.processInput(keyboardId, code, layerName)
  }   
}
