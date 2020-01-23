use cpython::{
    py_class, py_class_impl, py_coerce_item, py_module_initializer,
    PyObject, PyResult, PyString,
};

py_class!(class Logger |py| {
    data target: String;

    def __new__(_cls, target: PyString) -> PyResult<Logger> {
        let target = target.to_string(py)?.to_string();
        Logger::create_instance(py, target)
    }

    def log(&self, level: PyObject, msg: PyString, line: Option<PyObject>, module_path: Option<PyString>) -> PyResult<PyObject> {
        let level = match level.extract::<u32>(py).unwrap_or(100) {
            0..=9 => log::Level::Trace,
            10..=19 => log::Level::Debug,
            20..=29 => log::Level::Info,
            30..=39 => log::Level::Warn,
            _ => log::Level::Error,
        };
        let msg = msg.to_string(py)?;
        // let file = file.and_then(|x| x.to_string(py).ok().map(|x| x.to_string()));
        let line = line.and_then(|x| x.extract::<u32>(py).ok());
        let module_path = module_path.and_then(|x| x.to_string(py).ok().map(|x| x.to_string()));

        let meta = log::MetadataBuilder::new()
            .target(&self.target(py))
            .level(level)
            .build();

        log::logger().log(&log::Record::builder()
            .metadata(meta)
            .args(format_args!("{}", msg))
            .line(line)
            .file(module_path.as_ref().map(|x| &**x))
            .module_path(module_path.as_ref().map(|x| &**x))
            .build());
        
        Ok(py.None())
    }
});

py_module_initializer!(
    rust_logger,
    initrust_logger,
    PyInit_rust_logger,
    |py, m| {
        m.add(py, "__doc__", "Module documentation string")?;
        m.add_class::<Logger>(py)?;
        Ok(())
    }
);
