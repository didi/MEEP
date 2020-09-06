import style from './style';
import { h, Component } from 'preact';
import { connect } from 'react-redux';
import { setKeyboardMode } from '../../actions.js';

import VariableContainer from '../variable_container/index'
import Fuse from 'fuse.js'

class TemplateList extends Component {
    constructor(props) {
        super(props);
        this.state = {
            templates: [],
            flattenedTemplates: [],
            filteredResults: ''
        }
        this.handleChange = this.handleChange.bind(this)
        this.keyboardShortcuts = {}; // keys: 1-10, values: functions that should be called when key is pressed and input bar has focus
    }

    componentDidMount() {
        this.getTemplates();

        // prevent key presses in the search bar from triggering other events
        this.searchBar.addEventListener('keydown', e => {
            if (e.key == 'Escape') {
                // clear and unfocus
                this.searchBar.blur();
                this.searchBar.value = '';
                e.preventDefault();
            }
            else if (e.key == 'Tab') {
                // unfocus only
                this.searchBar.blur();
                e.preventDefault();
            }
            else if (!isNaN(parseInt(e.key))) {
                // handle key shortcuts
                this.keyboardShortcuts[parseInt(e.key)]();
                this.searchBar.blur();
                e.preventDefault();
            }
            e.stopPropagation();
        });

        // make / focus the search bar
        document.addEventListener('keydown', e => {
            if (e.key == '/') {
                this.searchBar.focus();
                e.preventDefault(); // prevent a slash from being typed
                e.stopPropagation();
            }
        });
    }

    handleChange() {
        let filteredResults = this.state.flattenedTemplates.map(t =>t.template);
        if (this.searchBar.value !== '') { // Fuse returns no results on empty string
            const fuse = new Fuse(this.state.flattenedTemplates, {
                matchAllTokens: true,
                threshold: 0.3,
                keys: [
                    {name: 'template', weight: 0.7},
                    {name: 'group', weight: 0.3}
                ],
                id: 'template'
            });
            filteredResults = fuse.search(this.searchBar.value);
        }
        this.setState(state => {
            return {
                ...state,
                filteredResults
            }
        });
    }

    flattenTemplates(templates) {
        return [].concat.apply([], templates.map(t=>t.templates))
    }

    async getTemplates() {
        const response = await fetch(process.env.SERVER_URL + ":" + process.env.SERVER_PORT + "/templates/" + this.props.sender);
        const templates = await response.json();
        const flattenedTemplates = this.flattenTemplates(templates);
        const filteredResults = flattenedTemplates.map(t =>t.template);

        this.setState({templates, flattenedTemplates, filteredResults});
    }

    async addTemplate(group) {
        const newTemplate = prompt("Enter your new template (use {} to specify parameters):");
        if (newTemplate === null) return;
        const requestBody = JSON.stringify({
            group: group,
            template: newTemplate
        });
        const response = await fetch(process.env.SERVER_URL + ":" + process.env.SERVER_PORT + "/templates/" + this.props.sender, {
            method: 'POST',
            body: requestBody,
            headers: new Headers({'content-type': 'application/json'}),
        });
        const templates = await response.json();
        const flattenedTemplates = this.flattenTemplates(templates);
        const filteredResults = flattenedTemplates.map(t =>t.template);
        this.setState({templates: templates, flattenedTemplates, filteredResults: filteredResults});
    }

    render(props, state) {
        let i = 1;
        return (
            <div class={"widget template-list " + style['template-list']}>
                <h3 id={style.templateHeader}>Templates</h3>
                <input onChange={this.handleChange} onFocus={
                    () => {
                        this.handleChange()
                        props.setKeyboardMode('templates');
                    }
                } onBlur={
                    () => {
                        this.handleChange();
                        props.setKeyboardMode('default');
                    }
                }
                    class={style.templateSearch} placeholder="Search" type="text" ref={input => this.searchBar = input}></input>
                <ul>
                    {state.templates.map(group => (
                      <li class={style.templateGroup}>
                        <h5 class={style.templateGroupHeader}>{group.groupDescription}</h5>
                        <div onclick={e => this.addTemplate(group.groupDescription)} class={style.addTemplateButton}>+</div>
                        {
                            group.templates.filter(t => state.filteredResults.includes(t.template)).map(t => {
                                const container = <VariableContainer key={t.template} string={t.template} params={t.params} variables={[]} group={group.groupDescription} type="template">{t}</VariableContainer>
                                let onSelect = () => {
                                    this.props.onTemplateClick(container);
                                    this.searchBar.value = '';
                                    this.handleChange();
                                };

                                // create keyboard shortcuts and hints
                                let keyboardHint = null;
                                if (props.keyboardMode === 'templates' && i <= 10) {
                                    this.keyboardShortcuts[i % 10] = onSelect;

                                    keyboardHint = <kbd>{i % 10}</kbd>;
                                    i += 1;
                                }

                                return (
                                  <div onclick={onSelect}>
                                    {keyboardHint}
                                    {container}
                                  </div>
                                );
                            })
                        }
                      </li>
                    ))}
                </ul>
            </div>
        );
    }
}

// subscribe to store updates
const mapStateToProps = (state, ownProps) => {
    return {
        keyboardMode: state.mode,
    }
};
const mapDispatchToProps = (dispatch, ownProps) => ({setKeyboardMode: (mode) => dispatch(setKeyboardMode(mode))});
export default connect(mapStateToProps, mapDispatchToProps)(TemplateList)

