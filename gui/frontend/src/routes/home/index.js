import { h, Component } from 'preact';
import style from './style';
import io from 'socket.io-client';

export default class Home extends Component {
    state = {
        rooms: []
    };

    componentDidMount() {
        document.title = `Dialog collection interface (${process.env.SERVER_PORT})`;
        this.loadRooms();
    }

    loadRooms = () => {
        fetch(process.env.SERVER_URL + ":" + process.env.SERVER_PORT + "/rooms", {method: 'GET'})
        .then(response => response.json())
        .then(rooms => {
            this.setState({
                rooms
            });
        });
    }

    render() {
        return this.state.rooms.length > 0 ? (
            <div className={style.rooms}>
                <h1>Available rooms:</h1>
                <table>
                    { this.state.rooms.map(room => (
                        <tr>
                          <td>Room: {room.id} {room.isEvaluation && <span> (evaluation)</span>}</td>
                          <td><a href={room.id +  "/user"}>User</a></td>
                          <td><a href={room.id + "/agent"}>Agent</a></td>
                        </tr>
                    )) }
                </table>
            </div>
        ) : (
            <h1 className={style.rooms}>No rooms found. Is the backend running?</h1>
        );
    }
}
