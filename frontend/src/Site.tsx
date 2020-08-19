import React from 'react';
import { List, Card } from 'antd';
import SearchForm from './SearchForm';
import Records from './Records';
import EpochRecord from './EpochRecord';

class Site extends React.Component {
    state = {
        records: []
    };

    updateRecords = (records: Array<{}>) => {
        this.setState({
            records: records
        });
    }

    render() {
        const { records } = this.state
        return (
            <div>
                <SearchForm updateRecords={this.updateRecords} />
                <Records records={records} />
            </div>
        );

    }
}

export default Site;
