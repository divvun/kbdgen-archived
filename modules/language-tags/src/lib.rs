#![allow(clippy::transmute_ptr_to_ptr, clippy::zero_ptr)] // clippy vs. cpython macros

use cpython::{
    py_class, py_module_initializer, PyDict, PyErr, PyList,
    PyObject, PyResult, PyString, ToPyObject,
};
use std::cell::RefCell;

py_class!(class LanguageTag |py| {
    data data: RefCell<language_tags::LanguageTag>;

    def __new__(_cls, arg: PyString) -> PyResult<LanguageTag> {
        let s = arg.to_string(py)?;
        let langtag: language_tags::LanguageTag = s.parse()
            .map_err(|e| PyErr::new::<cpython::exc::TypeError, _>(py, format!("{:?}", e)))?;
        LanguageTag::create_instance(py, RefCell::new(langtag))
    }

    def canonicalize(&self) -> PyResult<LanguageTag> {
        LanguageTag::create_instance(py, RefCell::new(self.data(py).borrow().canonicalize()))
    }

    def is_language_range(&self) -> PyResult<bool> {
        Ok(self.data(py).borrow().is_language_range())
    }

    def language(&self) -> PyResult<Option<PyString>> {
        Ok(self.data(py).borrow().language.as_ref().map(|x| x.to_py_object(py)))
    }

    def set_language(&self, language: Option<PyString>) -> PyResult<PyObject> {
        let mut data = self.data(py).try_borrow_mut()
            .map_err(|e| PyErr::new::<cpython::exc::TypeError, _>(py, format!("{:?}", e)))?;

        match language {
            Some(v) => {
                let s = v.to_string(py)?.to_string();
                data.language = Some(s);
            }
            None => { data.language = None; }
        }

        Ok(py.None())
    }

    def extlangs(&self) -> PyResult<PyList> {
        Ok(self.data(py).borrow().extlangs.to_py_object(py))
    }

    def script(&self) -> PyResult<Option<PyString>> {
        Ok(self.data(py).borrow().script.as_ref().map(|x| x.to_py_object(py)))
    }

    def set_script(&self, script: Option<PyString>) -> PyResult<PyObject> {
        let mut data = self.data(py).try_borrow_mut()
            .map_err(|e| PyErr::new::<cpython::exc::TypeError, _>(py, format!("{:?}", e)))?;

        match script {
            Some(v) => {
                let s = v.to_string(py)?.to_string();
                data.script = Some(s);
            }
            None => { data.script = None; }
        }

        Ok(py.None())
    }

    def region(&self) -> PyResult<Option<PyString>> {
        Ok(self.data(py).borrow().region.as_ref().map(|x| x.to_py_object(py)))
    }

    def set_region(&self, region: Option<PyString>) -> PyResult<PyObject> {
        let mut data = self.data(py).try_borrow_mut()
            .map_err(|e| PyErr::new::<cpython::exc::TypeError, _>(py, format!("{:?}", e)))?;

        match region {
            Some(v) => {
                let s = v.to_string(py)?.to_string();
                data.region = Some(s);
            }
            None => { data.region = None; }
        }

        Ok(py.None())
    }

    def variants(&self) -> PyResult<PyList> {
        Ok(self.data(py).borrow().variants.to_py_object(py))
    }

    def extensions(&self) -> PyResult<PyDict> {
        Ok(self.data(py).borrow().extensions.to_py_object(py))
    }

    def privateuse(&self) -> PyResult<PyList> {
        Ok(self.data(py).borrow().privateuse.to_py_object(py))
    }

    def __str__(&self) -> PyResult<PyString> {
        Ok(format!("{}", self.data(py).borrow()).to_py_object(py))
    }
});

py_module_initializer!(
    language_tags,
    initlanguage_tags,
    PyInit_language_tags,
    |py, m| {
        m.add(py, "__doc__", "Module documentation string")?;
        m.add_class::<LanguageTag>(py)?;
        Ok(())
    }
);
