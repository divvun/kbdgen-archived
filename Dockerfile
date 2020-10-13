FROM rust:buster

WORKDIR /usr/src/app

RUN cargo install pyoxidizer --vers 0.8.0

COPY . .

RUN cargo build

ENTRYPOINT [ "./target/debug/kbdgen" ]

