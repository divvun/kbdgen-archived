#![allow(clippy::transmute_ptr_to_ptr, clippy::zero_ptr)] // clippy vs. cpython macros

use cpython::{
    py_class, py_module_initializer, PyBytes, PyClone, PyObject, PyResult, PyString, PythonObject,
    ToPyObject,
};
use std::cell::RefCell;

py_class!(class Client |py| {
    data client: reqwest::blocking::Client;

    def __new__(_cls, user_agent: Option<PyString>) -> PyResult<Client> {
        let mut client_builder = reqwest::blocking::ClientBuilder::new();
        if let Some(user_agent) = user_agent {
            client_builder = client_builder.user_agent(&*user_agent.to_string(py)?);
        }
        Client::create_instance(py, client_builder.build().unwrap())
    }

    def get(&self, url: PyString) -> PyResult<RequestBuilder> {
        let client = self.client(py);
        let url = url.to_string(py)?;

        RequestBuilder::create_instance(py, RefCell::new(Some(client.get(&*url))))
    }

    def execute(&self, request: PyObject) -> PyResult<Response> {
        let request = request.extract::<Request>(py)?;
        let client = self.client(py);

        let res = client.execute(request.request(py).try_clone().unwrap()).unwrap();
        Response::create_instance(py, RefCell::new(Some(res)))
    }
});

py_class!(class Request |py| {
    data request: reqwest::blocking::Request;
});

py_class!(class Response |py| {
    data response: RefCell<Option<reqwest::blocking::Response>>;

    def text(&self) -> PyResult<PyObject> {
        let mut container = self.response(py).borrow_mut();
        if container.is_none() {
            return Ok(py.None());
        }

        let response = container.take().unwrap();
        Ok(response.text().unwrap().to_py_object(py).into_object())
    }

    def bytes(&self) -> PyResult<PyObject> {
        let mut container = self.response(py).borrow_mut();
        if container.is_none() {
            return Ok(py.None());
        }

        let response = container.take().unwrap();
        let bytes = response.bytes().unwrap();
        let bytes = PyBytes::new(py, &bytes);
        Ok(bytes.to_py_object(py).into_object())
    }
});

py_class!(class RequestBuilder |py| {
    data builder: RefCell<Option<reqwest::blocking::RequestBuilder>>;

    def header(&self, key: PyString, value: PyString) -> PyResult<Self> {
        let key = key.to_string(py)?;
        let value = value.to_string(py)?;

        let mut container = self.builder(py).borrow_mut();
        let builder = container.take().unwrap();

        *container = Some(builder.header(&*key, &*value));
        Ok(self.clone_ref(py))
    }

    def basic_auth(&self, username: PyString, password: PyString) -> PyResult<Self> {
        let username = username.to_string(py)?;
        let password = password.to_string(py)?;

        let mut container = self.builder(py).borrow_mut();
        let builder = container.take().unwrap();

        *container = Some(builder.basic_auth(&*username, Some(&*password)));
        Ok(self.clone_ref(py))
    }

    def send(&self) -> PyResult<Response> {
        let container = self.builder(py).borrow();
        let builder = container.as_ref().unwrap();
        let res = builder.try_clone().unwrap().send().unwrap();

        Response::create_instance(py, RefCell::new(Some(res)))
    }

    def build(&self) -> PyResult<Request> {
        let container = self.builder(py).borrow();
        let builder = container.as_ref().unwrap();
        let request = builder.try_clone().unwrap().build().unwrap();

        Request::create_instance(py, request)
    }
});

py_module_initializer!(reqwest, initreqwest, PyInit_reqwest, |py, m| {
    m.add(py, "__doc__", "Rust crate reqwest in Python")?;
    m.add_class::<Client>(py)?;
    m.add_class::<Request>(py)?;
    m.add_class::<RequestBuilder>(py)?;
    Ok(())
});
