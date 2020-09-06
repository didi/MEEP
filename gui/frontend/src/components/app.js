import "preact/debug";

import { h, Component } from 'preact';
import { Provider} from 'react-redux'
import { createStore } from 'redux'
import { Router } from 'preact-router';

import Header from './header';
import reducer from '../reducers'

// Code-splitting is automated for routes
import Agent from '../routes/agent';
import User from '../routes/user';
import TemplateUser from '../routes/template_user';
import Home from '../routes/home';

const store = createStore(reducer);

export default class App extends Component {
	
	/** Gets fired when the route changes.
	 *	@param {Object} event		"change" event from [preact-router](http://git.io/preact-router)
	 *	@param {string} event.url	The newly routed URL
	 */
	handleRoute = e => {
		this.currentUrl = e.url;
	};

	render() {
		return (
			<Provider store={store}>
				<div id="app">
					<Header />
					<Router onChange={this.handleRoute}>
						<Agent path=":roomId/agent" />
						<User path=":roomId/user" />
						<TemplateUser path=":roomId/template_user" />
						<Home default path="/" />
					</Router>
				</div>
			</Provider>
		);
	}
}
