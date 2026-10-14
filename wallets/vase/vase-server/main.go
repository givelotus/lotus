package main

import (
	"context"
	"log"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
	"vase.givelotus.org/server/initializers"
	"vase.givelotus.org/server/models"
)

type UserInfo struct {
	PushToken string   `json:"PushToken"`
	Longitude *float32 `json:"Longitude"`
	Latitude  *float32 `json:"Latitude"`
	Address   string   `json:"Address"`
}

func saveUserInfo(ctx context.Context, db *gorm.DB, info UserInfo) error {
	return db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if err := tx.Save(&models.User{PushToken: info.PushToken}).Error; err != nil {
			return err
		}
		if err := tx.Save(&models.Location{
			PushToken: info.PushToken,
			Longitude: *info.Longitude,
			Latitude:  *info.Latitude,
			Address:   info.Address,
		}).Error; err != nil {
			return err
		}
		return tx.Save(&models.Address{
			Type:      "XPI",
			PushToken: info.PushToken,
			Address:   info.Address,
		}).Error
	})
}

func newRouter(save func(context.Context, UserInfo) error) *gin.Engine {
	r := gin.New()
	r.Use(gin.Recovery())
	r.POST("/userinfo", func(c *gin.Context) {
		var info UserInfo
		if err := c.ShouldBindJSON(&info); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid user information"})
			return
		}
		if strings.TrimSpace(info.PushToken) == "" || strings.TrimSpace(info.Address) == "" ||
			info.Longitude == nil || info.Latitude == nil ||
			*info.Longitude < -180 || *info.Longitude > 180 ||
			*info.Latitude < -90 || *info.Latitude > 90 {
			c.JSON(http.StatusBadRequest, gin.H{"error": "PushToken, Address, and valid coordinates are required"})
			return
		}
		if err := save(c.Request.Context(), info); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Unable to save user information"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"info": info})
	})
	return r
}

func main() {
	initializers.LoadEnvVariables()
	db := initializers.ConnectToDB()
	r := newRouter(func(ctx context.Context, info UserInfo) error {
		return saveUserInfo(ctx, db, info)
	})
	if err := r.Run(); err != nil {
		log.Fatal(err)
	}
}
