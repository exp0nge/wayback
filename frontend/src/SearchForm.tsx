import React from 'react';
import { Layout, Menu, Breadcrumb, PageHeader, Input, Form, Spin, Alert } from 'antd';
import { Store } from 'antd/lib/form/interface';

const { Header, Content, Footer } = Layout;

type Props = {
    updateRecords: Function
};
type State = {};


class SearchForm extends React.Component<Props, State> {
    state = {
        loading: false
    };

    fetchHistory = (url: string, initial: boolean) => {
        const { updateRecords } = this.props;

        fetch(`https://viacors.azurewebsites.net/history?r=${url}`)
            .then(res => res.json())
            .then(
                (result) => {
                    if (!initial) {
                        this.setState({ loading: false });
                    }
                    updateRecords(result);
                },
                (error) => {
                    console.log('error', error);
                }
            );
    }

    onFinish = (values: Store) => {
        this.setState({ loading: true });
        const url = values.url;
        this.fetchHistory(url, true);

        fetch(`https://viacors.azurewebsites.net/?r=${url}`)
            .then(res => res.json())
            .then(
                (result) => {
                    this.fetchHistory(url, false);
                },
                (error) => {
                    this.setState({ loading: false });
                    console.log('error', error);
                }
            );
    };

    onFinishFailed = (errorInfo: any) => {
        console.log('Failed:', errorInfo);
    };

    render() {
        const { loading } = this.state;

        return (<Spin spinning={loading}>
            <Form
                name="basic"
                initialValues={{ remember: true }}
                onFinish={this.onFinish}
                onFinishFailed={this.onFinishFailed}
            >
                <Form.Item
                    label="URL"
                    name="url"
                    rules={[{ required: true, message: 'Please input a valid URL!' }]}
                >
                    <Input type="url" />
                </Form.Item>
            </Form>
        </Spin>);

    }
}

export default SearchForm;
