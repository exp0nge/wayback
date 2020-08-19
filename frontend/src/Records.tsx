import React from 'react';
import { List, Card } from 'antd';
import EpochRecord from './EpochRecord';


type Props = {
    records: Array<EpochRecord>
};
type State = {};


class Records extends React.Component<Props, State> {
    render() {
        const { records } = this.props;
        return (
            <List
                grid={{ gutter: 16, column: 4 }}
                dataSource={records}
                renderItem={record => {
                    const d = new Date(0);
                    d.setUTCSeconds(record.epoch);
                    return (<List.Item>
                        <Card title={d.toUTCString()}><a href={`https://siasky.net/${record.skylink}`}>{record.skylink}</a></Card>
                    </List.Item>);
                }}
            />
        );

    }
}

export default Records;
