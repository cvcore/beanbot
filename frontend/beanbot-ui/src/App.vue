<template>
    <div id="app">
      <beancount-editor />
    </div>
  </template>

  <script>
  import BeancountEditor from './components/BeancountEditor.vue';

  export default {
    name: 'App',
    components: {
      BeancountEditor
    }
  };
  </script>

  <style>
  #app {
    font-family: Avenir, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    color: #2c3e50;
    margin-top: 20px;
  }
  </style>
