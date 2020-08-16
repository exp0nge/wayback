import React, { FC } from 'react';
import './App.css';
import { Layout, Menu, Breadcrumb, PageHeader, Input, Form, Spin, Alert } from 'antd';
import { Store } from 'antd/lib/form/interface';
import SearchForm from './SearchForm';

const { Header, Content, Footer } = Layout;

const App: FC = () => {

  return (<div className="App">
    <Layout className="layout">
      <Content style={{ padding: '0 50px' }}>
        <PageHeader
          className="site-page-header"
          title="wayback"
        />
        <div className="site-layout-content">
          <SearchForm />
        </div>
      </Content>
      {/* <Footer style={{ textAlign: 'center' }}>@exp0nge</Footer> */}
    </Layout>
  </div>);
};

export default App;