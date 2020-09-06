import { combineReducers } from 'redux'
import VisibilityFilters from './actions'

const initialState = {
    mode: 'default',
}

function updateState(state=initialState, action) {

    // parse actions, return state
    switch (action.type) {
        case 'SET_KEYBOARD_MODE':
            return {
                mode: action.mode,
            }
        default:
            return state;
    }
}

// can use combineReducers here if we have multiple functions
const reducers = updateState;


export default reducers;