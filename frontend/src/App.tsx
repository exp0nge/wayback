import React, { FC } from 'react';
import './App.css';
import { Layout, PageHeader, Input, Form, Spin, Alert } from 'antd';
import Site from './Site';


const { Content, Footer } = Layout;

const App: FC = () => {
  return (<div className="App">
    <Layout className="layout">
      <Content style={{ padding: '0 50px' }}>
        <PageHeader
          className="site-page-header"
          title="wayback"
        />
        <div className="site-layout-content" style={{ height: "calc(100vh - 55px)" }}>
          <Site />
        </div>
      </Content>
      <Footer style={{ textAlign: 'center', position: "sticky", bottom: "0" }}><a href="https://github.com/exp0nge">@exp0nge</a></Footer>
    </Layout>
  </div>);
};

export default App;