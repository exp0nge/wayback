import React from 'react';
import { Layout, Menu, Breadcrumb, PageHeader, Input, Form, Spin, Alert } from 'antd';
import { Store } from 'antd/lib/form/interface';

const { Header, Content, Footer } = Layout;

class SearchForm extends React.Component {
    state = {
        loading: false
    };

    onFinish = (values: Store) => {
        this.setState({ loading: true });
        const url = values.url;
        fetch(`https://viacors.azurewebsites.net/?r=${url}`)
            .then(res => res.json())
            .then(
                (result) => {
                    this.setState({ loading: false });
                    console.log(result['sky_html_link']);
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
