import { createContext, useContext } from "react"

const BackendContext = createContext()
export const BACKEND_URL = "http://127.0.0.1:8000"

export const BackendProvider = ({ children }) => {
    return (
        <BackendContext.Provider value={{ BACKEND_URL }}>
            {children}
        </BackendContext.Provider>
    )
}

export const useBackend = () => useContext(BackendContext)