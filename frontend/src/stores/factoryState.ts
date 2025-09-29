import {defineStore} from 'pinia'

export const useFactoryState = defineStore('factory_state', {
    state: () => ({
        factoryList: [{'id':"占位"}],
        jobList: [{'id':"占位"}]
    }),
    actions: {
        install() {
            this.status = 'install';
        },
        uninstall() {
            this.status = 'uninstall';
        }
    }
})
