use indexmap::IndexMap;
use once_cell::sync::Lazy;

use crate::models::IsoKey;

pub(super) static MSKLC_KEYS: Lazy<IndexMap<IsoKey, (&str, &str)>> = Lazy::new(|| {
    [
        (IsoKey::E00, ("29", "OEM_3")),
        (IsoKey::E01, ("02", "1")),
        (IsoKey::E02, ("03", "2")),
        (IsoKey::E03, ("04", "3")),
        (IsoKey::E04, ("05", "4")),
        (IsoKey::E05, ("06", "5")),
        (IsoKey::E06, ("07", "6")),
        (IsoKey::E07, ("08", "7")),
        (IsoKey::E08, ("09", "8")),
        (IsoKey::E09, ("0a", "9")),
        (IsoKey::E10, ("0b", "0")),
        (IsoKey::E11, ("0c", "OEM_MINUS")),
        (IsoKey::E12, ("0d", "OEM_PLUS")),
        (IsoKey::D01, ("10", "Q")),
        (IsoKey::D02, ("11", "W")),
        (IsoKey::D03, ("12", "E")),
        (IsoKey::D04, ("13", "R")),
        (IsoKey::D05, ("14", "T")),
        (IsoKey::D06, ("15", "Y")),
        (IsoKey::D07, ("16", "U")),
        (IsoKey::D08, ("17", "I")),
        (IsoKey::D09, ("18", "O")),
        (IsoKey::D10, ("19", "P")),
        (IsoKey::D11, ("1a", "OEM_4")),
        (IsoKey::D12, ("1b", "OEM_6")),
        (IsoKey::C01, ("1e", "A")),
        (IsoKey::C02, ("1f", "S")),
        (IsoKey::C03, ("20", "D")),
        (IsoKey::C04, ("21", "F")),
        (IsoKey::C05, ("22", "G")),
        (IsoKey::C06, ("23", "H")),
        (IsoKey::C07, ("24", "J")),
        (IsoKey::C08, ("25", "K")),
        (IsoKey::C09, ("26", "L")),
        (IsoKey::C10, ("27", "OEM_1")),
        (IsoKey::C11, ("28", "OEM_7")),
        (IsoKey::C12, ("2b", "OEM_5")),
        (IsoKey::B00, ("56", "OEM_102")),
        (IsoKey::B01, ("2c", "Z")),
        (IsoKey::B02, ("2d", "X")),
        (IsoKey::B03, ("2e", "C")),
        (IsoKey::B04, ("2f", "V")),
        (IsoKey::B05, ("30", "B")),
        (IsoKey::B06, ("31", "N")),
        (IsoKey::B07, ("32", "M")),
        (IsoKey::B08, ("33", "OEM_COMMA")),
        (IsoKey::B09, ("34", "OEM_PERIOD")),
        (IsoKey::B10, ("35", "OEM_2")),
    ]
    .iter()
    .cloned()
    .collect()
});

pub(super) const FOOTER_CONTENT: &str = r#"
KEYNAME

01	Esc
0e	Backspace
0f	Tab
1c	Enter
1d	Ctrl
2a	Shift
36	"Right Shift"
37	"Num *"
38	Alt
39	Space
3a	"Caps Lock"
3b	F1
3c	F2
3d	F3
3e	F4
3f	F5
40	F6
41	F7
42	F8
43	F9
44	F10
45	Pause
46	"Scroll Lock"
47	"Num 7"
48	"Num 8"
49	"Num 9"
4a	"Num -"
4b	"Num 4"
4c	"Num 5"
4d	"Num 6"
4e	"Num +"
4f	"Num 1"
50	"Num 2"
51	"Num 3"
52	"Num 0"
53	"Num Del"
54	"Sys Req"
57	F11
58	F12
7c	F13
7d	F14
7e	F15
7f	F16
80	F17
81	F18
82	F19
83	F20
84	F21
85	F22
86	F23
87	F24

KEYNAME_EXT

1c	"Num Enter"
1d	"Right Ctrl"
35	"Num /"
37	"Prnt Scrn"
38	"Right Alt"
45	"Num Lock"
46	Break
47	Home
48	Up
49	"Page Up"
4b	Left
4d	Right
4f	End
50	Down
51	"Page Down"
52	Insert
53	Delete
54	<00>
56	Help
5b	"Left Windows"
5c	"Right Windows"
5d	Application
"#;
