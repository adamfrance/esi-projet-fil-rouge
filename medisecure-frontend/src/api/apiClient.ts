// medisecure-frontend/src/api/apiClient.ts
import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from "axios";
import { API_URL } from "./endpoints";

class ApiClient {
  private static instance: ApiClient;
  private axiosInstance: AxiosInstance;

  private constructor() {
    // S'assurer que l'URL de base se termine correctement pour éviter les doublons
    this.axiosInstance = axios.create({
      baseURL: API_URL, // Retirer le "/api" ici pour éviter la duplication
      headers: {
        "Content-Type": "application/json",
      },
      timeout: 15000, // Timeout plus long pour les environnements de développement
    });

    this.setupInterceptors();
  }

  public static getInstance(): ApiClient {
    if (!ApiClient.instance) {
      ApiClient.instance = new ApiClient();
    }
    return ApiClient.instance;
  }

  private setupInterceptors(): void {
    // Interceptor de requête - ajoute le token d'authentification
    this.axiosInstance.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem("access_token");
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        console.log(
          `Requête ${config.method?.toUpperCase()} vers ${config.url}`,
          config.data
        );
        return config;
      },
      (error) => {
        console.error("Erreur lors de la préparation de la requête:", error);
        return Promise.reject(error);
      }
    );

    // Interceptor de réponse - gère les erreurs d'authentification et les logs
    this.axiosInstance.interceptors.response.use(
      (response) => {
        console.log(`Réponse de ${response.config.url}:`, response.data);
        return response.data; // Retourne directement les données pour simplifier l'utilisation
      },
      async (error: AxiosError) => {
        if (error.response) {
          console.error(
            `Erreur ${error.response.status} pour ${error.config?.url}:`,
            error.response.data
          );

          // Si l'erreur est 401 (non autorisé), déconnexion
          if (
            error.response.status === 401 &&
            !error.config?.url?.includes("login")
          ) {
            console.warn("Token expiré ou invalide, déconnexion...");
            localStorage.removeItem("access_token");
            localStorage.removeItem("user");

            // Vérifier si nous sommes déjà sur la page de login pour éviter une boucle de redirections
            if (!window.location.pathname.includes("login")) {
              window.location.href = "/login";
            }
          }
        } else {
          console.error("Erreur réseau:", error.message);
        }
        return Promise.reject(error);
      }
    );
  }

  public async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    try {
      return await this.axiosInstance.get<T>(url, config);
    } catch (error) {
      console.error(`Erreur GET ${url}:`, error);
      throw error;
    }
  }

  public async post<T>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<T> {
    try {
      return await this.axiosInstance.post<T>(url, data, config);
    } catch (error) {
      console.error(`Erreur POST ${url}:`, error);
      throw error;
    }
  }

  public async put<T>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<T> {
    try {
      return await this.axiosInstance.put<T>(url, data, config);
    } catch (error) {
      console.error(`Erreur PUT ${url}:`, error);
      throw error;
    }
  }

  public async patch<T>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<T> {
    try {
      return await this.axiosInstance.patch<T>(url, data, config);
    } catch (error) {
      console.error(`Erreur PATCH ${url}:`, error);
      throw error;
    }
  }

  public async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    try {
      return await this.axiosInstance.delete<T>(url, config);
    } catch (error) {
      console.error(`Erreur DELETE ${url}:`, error);
      throw error;
    }
  }
}

export default ApiClient.getInstance();
