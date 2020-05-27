FROM rust:buster

WORKDIR /usr/src/app

RUN cargo install pyoxidizer --vers 0.7.0

COPY . .

RUN cargo build

CMD [ "./target/debug/kbdgen" ]


