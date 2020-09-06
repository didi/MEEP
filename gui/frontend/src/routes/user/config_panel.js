import { Component } from "preact";
import style from "./style";
import scriptLoader from "react-async-script-loader";

class ConfigPanel extends Component {
    constructor(props) {
        super(props);
        this.handleChange = this.handleChange.bind(this);
        this.handleSourceChange = this.handleSourceChange.bind(this);
        this.initGoogleMapsAutocomplete = this.initGoogleMapsAutocomplete.bind(
            this
        );
        this.state = {
            options: props.options
        };
        this.languages = [
            { code: "en", name: "English" },
            { code: "es", name: "Spanish" },
            { code: "zh", name: "Chinese" },
            { code: "fr", name: "French" },
            { code: "ru", name: "Russian" }
        ];
    }

    initGoogleMapsAutocomplete() {
        var defaultOrigin = new google.maps.LatLng(
            this.state.options.initialVariables.latitude,
            this.state.options.initialVariables.longitude
        );

        this.input = document.getElementById(style.sourceSearch);
        var options = {
            origin: defaultOrigin
        };

        this.autocomplete = new google.maps.places.Autocomplete(
            this.input,
            options
        );
        this.autocomplete.addListener("place_changed", this.handleSourceChange);
        this.enableEnterKey(this.input)
        google.maps.event.addDomListener(this.input, "keydown", function(
            event
        ) {
            if (event.keyCode === 13) {
                event.preventDefault();
            }
        });
    }

    enableEnterKey(input) {
        /* Store original event listener */
        const _addEventListener = input.addEventListener;

        const addEventListenerWrapper = (type, listener) => {
            if (type === "keydown") {
                /* Store existing listener function */
                const _listener = listener;
                listener = event => {
                    /* Simulate a 'down arrow' keypress if no address has been selected */
                    const suggestionSelected = document.getElementsByClassName(
                        "pac-item-selected"
                    ).length;
                    if (event.key === "Enter" && !suggestionSelected) {
                        const e = new KeyboardEvent("keydown", { key: "ArrowDown", code: "ArrowDown", keyCode: 40 });
                        _listener.apply(input, [e]);
                    }
                    _listener.apply(input, [event]);
                };
            }
            _addEventListener.apply(input, [type, listener]);
        };

        input.addEventListener = addEventListenerWrapper;
    }

    componentWillReceiveProps(newProps) {
        if (newProps.isScriptLoaded && newProps.isScriptLoadSucceed) {
            this.initGoogleMapsAutocomplete();
        }
        this.setState({
            options: newProps.options
        });
    }

    componentDidMount() {
        if (this.props.isScriptLoaded && this.props.isScriptLoadSucceed) {
            this.initGoogleMapsAutocomplete();
        }
    }

    handleSourceChange() {
        const place = this.autocomplete.getPlace();
        const newSource = {
            address: place.formatted_address,
            latitude: place.geometry.location.lat(),
            longitude: place.geometry.location.lng()
        };
        this.props.handleOptionChange(
            "initialVariables",
            newSource,
            () => (this.input.value = this.state.options.initialVariables.address)
        );
    }

    handleChange = option => e => {
        this.props.handleOptionChange(
            option,
            e.target.value,
            () => (e.target.checked = false)
        );
    };

    render() {
        return (
            <form class={style.configPanel}>
                <div class={style.configGroup}>
                    <h3 class={style.configHeader}>Starting address</h3>
                    <div>
                        <input
                            id={style.sourceSearch}
                            value={this.state.options.initialVariables.address}
                            type="text"
                        />
                    </div>
                </div>
                <div class={style.configGroup}>
                    <h3 class={style.configHeader}>Language</h3>
                    {this.languages.map((language, i) => {
                        return (
                            <div>
                                <input
                                    type="radio"
                                    value={language.code}
                                    onChange={this.handleChange(
                                        "inputLanguage"
                                    )}
                                    id={i}
                                    checked={
                                        this.state.options.inputLanguage ===
                                        language.code
                                    }
                                />
                                <label for={i}>{language.name}</label>
                            </div>
                        );
                    })}
                </div>
                <div class={style.configGroup}>
                    <h3 class={style.configHeader}>Input method</h3>
                    <div>
                        <input
                            type="radio"
                            value="text"
                            onChange={this.handleChange("inputType")}
                            checked={this.state.options.inputType === "text"}
                        />
                        <label>Text</label>
                    </div>
                    <div>
                        <input
                            type="radio"
                            value="speech"
                            onChange={this.handleChange("inputType")}
                            checked={this.state.options.inputType === "speech"}
                        />
                        <label>Speech</label>
                    </div>
                    { (Object.keys(this.state.options.userStory).length > 0) ? (
                        <button onClick={this.props.endDialog} type="button" disabled>
                        Abort dialog
                        </button>
                    ) : (
                        <button onClick={this.props.endDialog} type="button">
                        Abort dialog
                        </button>
                    )
                    }

                </div>
            </form>
        );
    }
}

export default scriptLoader([
    `http://maps.googleapis.com/maps/api/js?key=${process.env.GMAP_AUTOCOMPLETE_KEY}&libraries=places`
])(ConfigPanel);
